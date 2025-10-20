# Identity

Memory management for Bedrock AgentCore SDK.

## Service client

### `bedrock_agentcore.services.identity`

The main high-level client for the Bedrock AgentCore Identity service.

#### `IdentityClient`

A high-level client for Bedrock AgentCore Identity.

Source code in `bedrock_agentcore/services/identity.py`

```
class IdentityClient:
    """A high-level client for Bedrock AgentCore Identity."""

    def __init__(self, region: str):
        """Initialize the identity client with the specified region."""
        self.region = region
        self.cp_client = boto3.client(
            "bedrock-agentcore-control", region_name=region, endpoint_url=get_control_plane_endpoint(region)
        )
        self.identity_client = boto3.client(
            "bedrock-agentcore-control", region_name=region, endpoint_url=get_data_plane_endpoint(region)
        )
        self.dp_client = boto3.client(
            "bedrock-agentcore", region_name=region, endpoint_url=get_data_plane_endpoint(region)
        )
        self.logger = logging.getLogger("bedrock_agentcore.identity_client")

    def create_oauth2_credential_provider(self, req):
        """Create an OAuth2 credential provider."""
        self.logger.info("Creating OAuth2 credential provider...")
        return self.cp_client.create_oauth2_credential_provider(**req)

    def create_api_key_credential_provider(self, req):
        """Create an API key credential provider."""
        self.logger.info("Creating API key credential provider...")
        return self.cp_client.create_api_key_credential_provider(**req)

    def get_workload_access_token(
        self, workload_name: str, user_token: Optional[str] = None, user_id: Optional[str] = None
    ) -> Dict:
        """Get a workload access token using workload name and optionally user token."""
        if user_token:
            if user_id is not None:
                self.logger.warning("Both user token and user id are supplied, using user token")
            self.logger.info("Getting workload access token for JWT...")
            resp = self.dp_client.get_workload_access_token_for_jwt(workloadName=workload_name, userToken=user_token)
        elif user_id:
            self.logger.info("Getting workload access token for user id...")
            resp = self.dp_client.get_workload_access_token_for_user_id(workloadName=workload_name, userId=user_id)
        else:
            self.logger.info("Getting workload access token...")
            resp = self.dp_client.get_workload_access_token(workloadName=workload_name)

        self.logger.info("Successfully retrieved workload access token")
        return resp

    def create_workload_identity(
        self, name: Optional[str] = None, allowed_resource_oauth_2_return_urls: Optional[list[str]] = None
    ) -> Dict:
        """Create workload identity with optional name."""
        self.logger.info("Creating workload identity...")
        if not name:
            name = f"workload-{uuid.uuid4().hex[:8]}"
        return self.identity_client.create_workload_identity(
            name=name, allowedResourceOauth2ReturnUrls=allowed_resource_oauth_2_return_urls or []
        )

    def update_workload_identity(self, name: str, allowed_resource_oauth_2_return_urls: list[str]) -> Dict:
        """Update an existing workload identity with allowed resource OAuth2 callback urls."""
        self.logger.info(
            "Updating workload identity '%s' with callback urls: %s", name, allowed_resource_oauth_2_return_urls
        )
        return self.identity_client.update_workload_identity(
            name=name, allowedResourceOauth2ReturnUrls=allowed_resource_oauth_2_return_urls
        )

    def get_workload_identity(self, name: str) -> Dict:
        """Retrieves information about a workload identity."""
        self.logger.info("Fetching workload identity '%s'", name)
        return self.cp_client.get_workload_identity(name=name)

    def complete_resource_token_auth(
        self, session_uri: str, user_identifier: Union[UserTokenIdentifier, UserIdIdentifier]
    ):
        """Confirms the user authentication session for obtaining OAuth2.0 tokens for a resource."""
        self.logger.info("Completing 3LO OAuth2 flow...")

        user_identifier_value = {}
        if isinstance(user_identifier, UserIdIdentifier):
            user_identifier_value["userId"] = user_identifier.user_id
        elif isinstance(user_identifier, UserTokenIdentifier):
            user_identifier_value["userToken"] = user_identifier.user_token
        else:
            raise ValueError(f"Unexpected UserIdentifier: {user_identifier}")

        return self.dp_client.complete_resource_token_auth(userIdentifier=user_identifier_value, sessionUri=session_uri)

    async def get_token(
        self,
        *,
        provider_name: str,
        scopes: Optional[List[str]] = None,
        agent_identity_token: str,
        on_auth_url: Optional[Callable[[str], Any]] = None,
        auth_flow: Literal["M2M", "USER_FEDERATION"],
        callback_url: Optional[str] = None,
        force_authentication: bool = False,
        token_poller: Optional[TokenPoller] = None,
        custom_state: Optional[str] = None,
    ) -> str:
        """Get an OAuth2 access token for the specified provider.

        Args:
            provider_name: The credential provider name
            scopes: Optional list of OAuth2 scopes to request
            agent_identity_token: Agent identity token for authentication
            on_auth_url: Callback for handling authorization URLs
            auth_flow: Authentication flow type ("M2M" or "USER_FEDERATION")
            callback_url: OAuth2 callback URL (must be pre-registered)
            force_authentication: Force re-authentication even if token exists in the token vault
            token_poller: Custom token poller implementation
            custom_state: A state that allows applications to verify the validity of callbacks to callback_url

        Returns:
            The access token string

        Raises:
            RequiresUserConsentException: When user consent is needed
            Various other exceptions for error conditions
        """
        self.logger.info("Getting OAuth2 token...")

        # Build parameters
        req = {
            "resourceCredentialProviderName": provider_name,
            "scopes": scopes,
            "oauth2Flow": auth_flow,
            "workloadIdentityToken": agent_identity_token,
        }

        # Add optional parameters
        if callback_url:
            req["resourceOauth2ReturnUrl"] = callback_url
        if force_authentication:
            req["forceAuthentication"] = force_authentication
        if custom_state:
            req["customState"] = custom_state

        response = self.dp_client.get_resource_oauth2_token(**req)

        # If we got a token directly, return it
        if "accessToken" in response:
            return response["accessToken"]

        # If we got an authorization URL, handle the OAuth flow
        if "authorizationUrl" in response:
            auth_url = response["authorizationUrl"]
            # Notify about the auth URL if callback provided
            if on_auth_url:
                if asyncio.iscoroutinefunction(on_auth_url):
                    await on_auth_url(auth_url)
                else:
                    on_auth_url(auth_url)

            # only the initial request should have force authentication
            if force_authentication:
                req["forceAuthentication"] = False

            if "sessionUri" in response:
                req["sessionUri"] = response["sessionUri"]

            # Poll for the token
            active_poller = token_poller or _DefaultApiTokenPoller(
                auth_url, lambda: self.dp_client.get_resource_oauth2_token(**req).get("accessToken", None)
            )
            return await active_poller.poll_for_token()

        raise RuntimeError("Identity service did not return a token or an authorization URL.")

    async def get_api_key(self, *, provider_name: str, agent_identity_token: str) -> str:
        """Programmatically retrieves an API key from the Identity service."""
        self.logger.info("Getting API key...")
        req = {"resourceCredentialProviderName": provider_name, "workloadIdentityToken": agent_identity_token}

        return self.dp_client.get_resource_api_key(**req)["apiKey"]
```

##### `__init__(region)`

Initialize the identity client with the specified region.

Source code in `bedrock_agentcore/services/identity.py`

```
def __init__(self, region: str):
    """Initialize the identity client with the specified region."""
    self.region = region
    self.cp_client = boto3.client(
        "bedrock-agentcore-control", region_name=region, endpoint_url=get_control_plane_endpoint(region)
    )
    self.identity_client = boto3.client(
        "bedrock-agentcore-control", region_name=region, endpoint_url=get_data_plane_endpoint(region)
    )
    self.dp_client = boto3.client(
        "bedrock-agentcore", region_name=region, endpoint_url=get_data_plane_endpoint(region)
    )
    self.logger = logging.getLogger("bedrock_agentcore.identity_client")
```

##### `complete_resource_token_auth(session_uri, user_identifier)`

Confirms the user authentication session for obtaining OAuth2.0 tokens for a resource.

Source code in `bedrock_agentcore/services/identity.py`

```
def complete_resource_token_auth(
    self, session_uri: str, user_identifier: Union[UserTokenIdentifier, UserIdIdentifier]
):
    """Confirms the user authentication session for obtaining OAuth2.0 tokens for a resource."""
    self.logger.info("Completing 3LO OAuth2 flow...")

    user_identifier_value = {}
    if isinstance(user_identifier, UserIdIdentifier):
        user_identifier_value["userId"] = user_identifier.user_id
    elif isinstance(user_identifier, UserTokenIdentifier):
        user_identifier_value["userToken"] = user_identifier.user_token
    else:
        raise ValueError(f"Unexpected UserIdentifier: {user_identifier}")

    return self.dp_client.complete_resource_token_auth(userIdentifier=user_identifier_value, sessionUri=session_uri)
```

##### `create_api_key_credential_provider(req)`

Create an API key credential provider.

Source code in `bedrock_agentcore/services/identity.py`

```
def create_api_key_credential_provider(self, req):
    """Create an API key credential provider."""
    self.logger.info("Creating API key credential provider...")
    return self.cp_client.create_api_key_credential_provider(**req)
```

##### `create_oauth2_credential_provider(req)`

Create an OAuth2 credential provider.

Source code in `bedrock_agentcore/services/identity.py`

```
def create_oauth2_credential_provider(self, req):
    """Create an OAuth2 credential provider."""
    self.logger.info("Creating OAuth2 credential provider...")
    return self.cp_client.create_oauth2_credential_provider(**req)
```

##### `create_workload_identity(name=None, allowed_resource_oauth_2_return_urls=None)`

Create workload identity with optional name.

Source code in `bedrock_agentcore/services/identity.py`

```
def create_workload_identity(
    self, name: Optional[str] = None, allowed_resource_oauth_2_return_urls: Optional[list[str]] = None
) -> Dict:
    """Create workload identity with optional name."""
    self.logger.info("Creating workload identity...")
    if not name:
        name = f"workload-{uuid.uuid4().hex[:8]}"
    return self.identity_client.create_workload_identity(
        name=name, allowedResourceOauth2ReturnUrls=allowed_resource_oauth_2_return_urls or []
    )
```

##### `get_api_key(*, provider_name, agent_identity_token)`

Programmatically retrieves an API key from the Identity service.

Source code in `bedrock_agentcore/services/identity.py`

```
async def get_api_key(self, *, provider_name: str, agent_identity_token: str) -> str:
    """Programmatically retrieves an API key from the Identity service."""
    self.logger.info("Getting API key...")
    req = {"resourceCredentialProviderName": provider_name, "workloadIdentityToken": agent_identity_token}

    return self.dp_client.get_resource_api_key(**req)["apiKey"]
```

##### `get_token(*, provider_name, scopes=None, agent_identity_token, on_auth_url=None, auth_flow, callback_url=None, force_authentication=False, token_poller=None, custom_state=None)`

Get an OAuth2 access token for the specified provider.

Parameters:

| Name                   | Type                                | Description                                                                          | Default    |
| ---------------------- | ----------------------------------- | ------------------------------------------------------------------------------------ | ---------- |
| `provider_name`        | `str`                               | The credential provider name                                                         | *required* |
| `scopes`               | `Optional[List[str]]`               | Optional list of OAuth2 scopes to request                                            | `None`     |
| `agent_identity_token` | `str`                               | Agent identity token for authentication                                              | *required* |
| `on_auth_url`          | `Optional[Callable[[str], Any]]`    | Callback for handling authorization URLs                                             | `None`     |
| `auth_flow`            | `Literal['M2M', 'USER_FEDERATION']` | Authentication flow type ("M2M" or "USER_FEDERATION")                                | *required* |
| `callback_url`         | `Optional[str]`                     | OAuth2 callback URL (must be pre-registered)                                         | `None`     |
| `force_authentication` | `bool`                              | Force re-authentication even if token exists in the token vault                      | `False`    |
| `token_poller`         | `Optional[TokenPoller]`             | Custom token poller implementation                                                   | `None`     |
| `custom_state`         | `Optional[str]`                     | A state that allows applications to verify the validity of callbacks to callback_url | `None`     |

Returns:

| Type  | Description             |
| ----- | ----------------------- |
| `str` | The access token string |

Raises:

| Type                           | Description                 |
| ------------------------------ | --------------------------- |
| `RequiresUserConsentException` | When user consent is needed |

Source code in `bedrock_agentcore/services/identity.py`

```
async def get_token(
    self,
    *,
    provider_name: str,
    scopes: Optional[List[str]] = None,
    agent_identity_token: str,
    on_auth_url: Optional[Callable[[str], Any]] = None,
    auth_flow: Literal["M2M", "USER_FEDERATION"],
    callback_url: Optional[str] = None,
    force_authentication: bool = False,
    token_poller: Optional[TokenPoller] = None,
    custom_state: Optional[str] = None,
) -> str:
    """Get an OAuth2 access token for the specified provider.

    Args:
        provider_name: The credential provider name
        scopes: Optional list of OAuth2 scopes to request
        agent_identity_token: Agent identity token for authentication
        on_auth_url: Callback for handling authorization URLs
        auth_flow: Authentication flow type ("M2M" or "USER_FEDERATION")
        callback_url: OAuth2 callback URL (must be pre-registered)
        force_authentication: Force re-authentication even if token exists in the token vault
        token_poller: Custom token poller implementation
        custom_state: A state that allows applications to verify the validity of callbacks to callback_url

    Returns:
        The access token string

    Raises:
        RequiresUserConsentException: When user consent is needed
        Various other exceptions for error conditions
    """
    self.logger.info("Getting OAuth2 token...")

    # Build parameters
    req = {
        "resourceCredentialProviderName": provider_name,
        "scopes": scopes,
        "oauth2Flow": auth_flow,
        "workloadIdentityToken": agent_identity_token,
    }

    # Add optional parameters
    if callback_url:
        req["resourceOauth2ReturnUrl"] = callback_url
    if force_authentication:
        req["forceAuthentication"] = force_authentication
    if custom_state:
        req["customState"] = custom_state

    response = self.dp_client.get_resource_oauth2_token(**req)

    # If we got a token directly, return it
    if "accessToken" in response:
        return response["accessToken"]

    # If we got an authorization URL, handle the OAuth flow
    if "authorizationUrl" in response:
        auth_url = response["authorizationUrl"]
        # Notify about the auth URL if callback provided
        if on_auth_url:
            if asyncio.iscoroutinefunction(on_auth_url):
                await on_auth_url(auth_url)
            else:
                on_auth_url(auth_url)

        # only the initial request should have force authentication
        if force_authentication:
            req["forceAuthentication"] = False

        if "sessionUri" in response:
            req["sessionUri"] = response["sessionUri"]

        # Poll for the token
        active_poller = token_poller or _DefaultApiTokenPoller(
            auth_url, lambda: self.dp_client.get_resource_oauth2_token(**req).get("accessToken", None)
        )
        return await active_poller.poll_for_token()

    raise RuntimeError("Identity service did not return a token or an authorization URL.")
```

##### `get_workload_access_token(workload_name, user_token=None, user_id=None)`

Get a workload access token using workload name and optionally user token.

Source code in `bedrock_agentcore/services/identity.py`

```
def get_workload_access_token(
    self, workload_name: str, user_token: Optional[str] = None, user_id: Optional[str] = None
) -> Dict:
    """Get a workload access token using workload name and optionally user token."""
    if user_token:
        if user_id is not None:
            self.logger.warning("Both user token and user id are supplied, using user token")
        self.logger.info("Getting workload access token for JWT...")
        resp = self.dp_client.get_workload_access_token_for_jwt(workloadName=workload_name, userToken=user_token)
    elif user_id:
        self.logger.info("Getting workload access token for user id...")
        resp = self.dp_client.get_workload_access_token_for_user_id(workloadName=workload_name, userId=user_id)
    else:
        self.logger.info("Getting workload access token...")
        resp = self.dp_client.get_workload_access_token(workloadName=workload_name)

    self.logger.info("Successfully retrieved workload access token")
    return resp
```

##### `get_workload_identity(name)`

Retrieves information about a workload identity.

Source code in `bedrock_agentcore/services/identity.py`

```
def get_workload_identity(self, name: str) -> Dict:
    """Retrieves information about a workload identity."""
    self.logger.info("Fetching workload identity '%s'", name)
    return self.cp_client.get_workload_identity(name=name)
```

##### `update_workload_identity(name, allowed_resource_oauth_2_return_urls)`

Update an existing workload identity with allowed resource OAuth2 callback urls.

Source code in `bedrock_agentcore/services/identity.py`

```
def update_workload_identity(self, name: str, allowed_resource_oauth_2_return_urls: list[str]) -> Dict:
    """Update an existing workload identity with allowed resource OAuth2 callback urls."""
    self.logger.info(
        "Updating workload identity '%s' with callback urls: %s", name, allowed_resource_oauth_2_return_urls
    )
    return self.identity_client.update_workload_identity(
        name=name, allowedResourceOauth2ReturnUrls=allowed_resource_oauth_2_return_urls
    )
```

#### `TokenPoller`

Bases: `ABC`

Abstract base class for token polling implementations.

Source code in `bedrock_agentcore/services/identity.py`

```
class TokenPoller(ABC):
    """Abstract base class for token polling implementations."""

    @abstractmethod
    async def poll_for_token(self) -> str:
        """Poll for a token and return it when available."""
        raise NotImplementedError
```

##### `poll_for_token()`

Poll for a token and return it when available.

Source code in `bedrock_agentcore/services/identity.py`

```
@abstractmethod
async def poll_for_token(self) -> str:
    """Poll for a token and return it when available."""
    raise NotImplementedError
```

#### `UserIdIdentifier`

Bases: `BaseModel`

The ID of the user for whom you have retrieved a workload access token for.

Source code in `bedrock_agentcore/services/identity.py`

```
class UserIdIdentifier(BaseModel):
    """The ID of the user for whom you have retrieved a workload access token for."""

    user_id: str
```

#### `UserTokenIdentifier`

Bases: `BaseModel`

The OAuth2.0 token issued by the user's identity provider.

Source code in `bedrock_agentcore/services/identity.py`

```
class UserTokenIdentifier(BaseModel):
    """The OAuth2.0 token issued by the user's identity provider."""

    user_token: str
```

## Decorators

### `bedrock_agentcore.identity`

Bedrock AgentCore SDK identity package.

#### `requires_access_token(*, provider_name, into='access_token', scopes, on_auth_url=None, auth_flow, callback_url=None, force_authentication=False, token_poller=None, custom_state=None)`

Decorator that fetches an OAuth2 access token before calling the decorated function.

Parameters:

| Name                   | Type                                | Description                                                                          | Default          |
| ---------------------- | ----------------------------------- | ------------------------------------------------------------------------------------ | ---------------- |
| `provider_name`        | `str`                               | The credential provider name                                                         | *required*       |
| `into`                 | `str`                               | Parameter name to inject the token into                                              | `'access_token'` |
| `scopes`               | `List[str]`                         | OAuth2 scopes to request                                                             | *required*       |
| `on_auth_url`          | `Optional[Callable[[str], Any]]`    | Callback for handling authorization URLs                                             | `None`           |
| `auth_flow`            | `Literal['M2M', 'USER_FEDERATION']` | Authentication flow type ("M2M" or "USER_FEDERATION")                                | *required*       |
| `callback_url`         | `Optional[str]`                     | OAuth2 callback URL                                                                  | `None`           |
| `force_authentication` | `bool`                              | Force re-authentication                                                              | `False`          |
| `token_poller`         | `Optional[TokenPoller]`             | Custom token poller implementation                                                   | `None`           |
| `custom_state`         | `Optional[str]`                     | A state that allows applications to verify the validity of callbacks to callback_url | `None`           |

Returns:

| Type       | Description        |
| ---------- | ------------------ |
| `Callable` | Decorator function |

Source code in `bedrock_agentcore/identity/auth.py`

```
def requires_access_token(
    *,
    provider_name: str,
    into: str = "access_token",
    scopes: List[str],
    on_auth_url: Optional[Callable[[str], Any]] = None,
    auth_flow: Literal["M2M", "USER_FEDERATION"],
    callback_url: Optional[str] = None,
    force_authentication: bool = False,
    token_poller: Optional[TokenPoller] = None,
    custom_state: Optional[str] = None,
) -> Callable:
    """Decorator that fetches an OAuth2 access token before calling the decorated function.

    Args:
        provider_name: The credential provider name
        into: Parameter name to inject the token into
        scopes: OAuth2 scopes to request
        on_auth_url: Callback for handling authorization URLs
        auth_flow: Authentication flow type ("M2M" or "USER_FEDERATION")
        callback_url: OAuth2 callback URL
        force_authentication: Force re-authentication
        token_poller: Custom token poller implementation
        custom_state: A state that allows applications to verify the validity of callbacks to callback_url

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        client = IdentityClient(_get_region())

        async def _get_token() -> str:
            """Common token fetching logic."""
            return await client.get_token(
                provider_name=provider_name,
                agent_identity_token=await _get_workload_access_token(client),
                scopes=scopes,
                on_auth_url=on_auth_url,
                auth_flow=auth_flow,
                callback_url=_get_oauth2_callback_url(callback_url),
                force_authentication=force_authentication,
                token_poller=token_poller,
                custom_state=custom_state,
            )

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs_func: Any) -> Any:
            token = await _get_token()
            kwargs_func[into] = token
            return await func(*args, **kwargs_func)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs_func: Any) -> Any:
            if _has_running_loop():
                # for async env, eg. runtime
                ctx = contextvars.copy_context()
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(ctx.run, asyncio.run, _get_token())
                    token = future.result()
            else:
                # for sync env, eg. local dev
                token = asyncio.run(_get_token())

            kwargs_func[into] = token
            return func(*args, **kwargs_func)

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
```

#### `requires_api_key(*, provider_name, into='api_key')`

Decorator that fetches an API key before calling the decorated function.

Parameters:

| Name            | Type  | Description                               | Default     |
| --------------- | ----- | ----------------------------------------- | ----------- |
| `provider_name` | `str` | The credential provider name              | *required*  |
| `into`          | `str` | Parameter name to inject the API key into | `'api_key'` |

Returns:

| Type       | Description        |
| ---------- | ------------------ |
| `Callable` | Decorator function |

Source code in `bedrock_agentcore/identity/auth.py`

```
def requires_api_key(*, provider_name: str, into: str = "api_key") -> Callable:
    """Decorator that fetches an API key before calling the decorated function.

    Args:
        provider_name: The credential provider name
        into: Parameter name to inject the API key into

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        client = IdentityClient(_get_region())

        async def _get_api_key():
            return await client.get_api_key(
                provider_name=provider_name,
                agent_identity_token=await _get_workload_access_token(client),
            )

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            api_key = await _get_api_key()
            kwargs[into] = api_key
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            if _has_running_loop():
                # for async env, eg. runtime
                ctx = contextvars.copy_context()
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(ctx.run, asyncio.run, _get_api_key())
                    api_key = future.result()
            else:
                # for sync env, eg. local dev
                api_key = asyncio.run(_get_api_key())

            kwargs[into] = api_key
            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
```
