# Runtime

Runtime management and application context for Bedrock AgentCore.

## `bedrock_agentcore.runtime`

BedrockAgentCore Runtime Package.

This package contains the core runtime components for Bedrock AgentCore applications:

- BedrockAgentCoreApp: Main application class
- RequestContext: HTTP request context
- BedrockAgentCoreContext: Agent identity context

### `AgentCoreRuntimeClient`

Client for generating WebSocket authentication for AgentCore Runtime.

This client provides authentication credentials for WebSocket connections to AgentCore Runtime endpoints, allowing applications to establish bidirectional streaming connections with agent runtimes.

Attributes:

| Name      | Type      | Description                            |
| --------- | --------- | -------------------------------------- |
| `region`  | `str`     | The AWS region being used.             |
| `session` | `Session` | The boto3 session for AWS credentials. |

Source code in `bedrock_agentcore/runtime/agent_core_runtime_client.py`

```
class AgentCoreRuntimeClient:
    """Client for generating WebSocket authentication for AgentCore Runtime.

    This client provides authentication credentials for WebSocket connections
    to AgentCore Runtime endpoints, allowing applications to establish
    bidirectional streaming connections with agent runtimes.

    Attributes:
        region (str): The AWS region being used.
        session (boto3.Session): The boto3 session for AWS credentials.
    """

    def __init__(self, region: str, session: Optional[boto3.Session] = None) -> None:
        """Initialize an AgentCoreRuntime client for the specified AWS region.

        Args:
            region (str): The AWS region to use for the AgentCore Runtime service.
            session (Optional[boto3.Session]): Optional boto3 session. If not provided,
                a new session will be created using default credentials.
        """
        self.region = region
        self.logger = logging.getLogger(__name__)

        if session is None:
            session = boto3.Session()

        self.session = session

    def _parse_runtime_arn(self, runtime_arn: str) -> Dict[str, str]:
        """Parse runtime ARN and extract components.

        Args:
            runtime_arn (str): Full runtime ARN

        Returns:
            Dict[str, str]: Dictionary with region, account_id, runtime_id

        Raises:
            ValueError: If ARN format is invalid
        """
        # Expected format: arn:aws:bedrock-agentcore:{region}:{account}:runtime/{runtime_id}
        parts = runtime_arn.split(":")

        if len(parts) != 6:
            raise ValueError(f"Invalid runtime ARN format: {runtime_arn}")

        if parts[0] != "arn" or parts[1] != "aws" or parts[2] != "bedrock-agentcore":
            raise ValueError(f"Invalid runtime ARN format: {runtime_arn}")

        # Parse the resource part (runtime/{runtime_id})
        resource = parts[5]
        if not resource.startswith("runtime/"):
            raise ValueError(f"Invalid runtime ARN format: {runtime_arn}")

        runtime_id = resource.split("/", 1)[1]

        # Validate that components are not empty
        region = parts[3]
        account_id = parts[4]

        if not region or not account_id or not runtime_id:
            raise ValueError("ARN components cannot be empty")

        return {
            "region": region,
            "account_id": account_id,
            "runtime_id": runtime_id,
        }

    def _build_websocket_url(
        self,
        runtime_arn: str,
        endpoint_name: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> str:
        """Build WebSocket URL with query parameters.

        Args:
            runtime_arn (str): Full runtime ARN
            endpoint_name (Optional[str]): Optional endpoint name for qualifier param
            custom_headers (Optional[Dict[str, str]]): Optional custom query parameters

        Returns:
            str: WebSocket URL with query parameters
        """
        # Get the data plane endpoint
        host = get_data_plane_endpoint(self.region).replace("https://", "")

        # URL-encode the runtime ARN
        encoded_arn = quote(runtime_arn, safe="")

        # Build base path
        path = f"/runtimes/{encoded_arn}/ws"

        # Build query parameters
        query_params = {}

        if endpoint_name:
            query_params["qualifier"] = endpoint_name

        if custom_headers:
            query_params.update(custom_headers)

        # Construct URL
        if query_params:
            query_string = urlencode(query_params)
            ws_url = f"wss://{host}{path}?{query_string}"
        else:
            ws_url = f"wss://{host}{path}"

        return ws_url

    def generate_ws_connection(
        self,
        runtime_arn: str,
        session_id: Optional[str] = None,
        endpoint_name: Optional[str] = None,
    ) -> Tuple[str, Dict[str, str]]:
        """Generate WebSocket URL and SigV4 signed headers for runtime connection.

        Args:
            runtime_arn (str): Full runtime ARN
                (e.g., 'arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime-abc')
            session_id (Optional[str]): Session ID to use. If None, auto-generates a UUID.
            endpoint_name (Optional[str]): Endpoint name to use as 'qualifier' query parameter.
                If provided, adds ?qualifier={endpoint_name} to the URL.

        Returns:
            Tuple[str, Dict[str, str]]: A tuple containing:
                - WebSocket URL (wss://...) with query parameters
                - Headers dictionary with SigV4 signature

        Raises:
            RuntimeError: If no AWS credentials are found.
            ValueError: If runtime_arn format is invalid.

        Example:
            >>> client = AgentRuntimeClient('us-west-2')
            >>> ws_url, headers = client.generate_ws_connection(
            ...     runtime_arn='arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime',
            ...     endpoint_name='DEFAULT'
            ... )
        """
        self.logger.info("Generating WebSocket connection credentials...")

        # Validate ARN
        self._parse_runtime_arn(runtime_arn)

        # Auto-generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            self.logger.debug("Auto-generated session ID: %s", session_id)

        # Build WebSocket URL
        ws_url = self._build_websocket_url(runtime_arn, endpoint_name)

        # Get AWS credentials
        credentials = self.session.get_credentials()
        if not credentials:
            raise RuntimeError("No AWS credentials found")

        frozen_credentials = credentials.get_frozen_credentials()

        # Convert wss:// to https:// for signing
        https_url = ws_url.replace("wss://", "https://")
        parsed = urlparse(https_url)
        host = parsed.netloc

        # Create the request to sign
        request = AWSRequest(
            method="GET",
            url=https_url,
            headers={
                "host": host,
                "x-amz-date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            },
        )

        # Sign the request with SigV4
        auth = SigV4Auth(frozen_credentials, "bedrock-agentcore", self.region)
        auth.add_auth(request)

        # Build headers for WebSocket connection
        headers = {
            "Host": host,
            "X-Amz-Date": request.headers["x-amz-date"],
            "Authorization": request.headers["Authorization"],
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Version": "13",
            "Sec-WebSocket-Key": base64.b64encode(secrets.token_bytes(16)).decode(),
            "User-Agent": f"AgentRuntime-Client/1.0 (Session: {session_id})",
        }

        # Add session token if present
        if frozen_credentials.token:
            headers["X-Amz-Security-Token"] = frozen_credentials.token

        self.logger.info("✓ WebSocket connection credentials generated (Session: %s)", session_id)
        return ws_url, headers

    def generate_presigned_url(
        self,
        runtime_arn: str,
        session_id: Optional[str] = None,
        endpoint_name: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        expires: int = DEFAULT_PRESIGNED_URL_TIMEOUT,
    ) -> str:
        """Generate a presigned WebSocket URL for runtime connection.

        Presigned URLs include authentication in query parameters, allowing
        frontend clients to connect without managing AWS credentials.

        Args:
            runtime_arn (str): Full runtime ARN
                (e.g., 'arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime-abc')
            session_id (Optional[str]): Session ID to use. If None, auto-generates a UUID.
            endpoint_name (Optional[str]): Endpoint name to use as 'qualifier' query parameter.
                If provided, adds ?qualifier={endpoint_name} to the URL before signing.
            custom_headers (Optional[Dict[str, str]]): Additional query parameters to include
                in the presigned URL before signing (e.g., {"abc": "pqr"}).
            expires (int): Seconds until URL expires (default: 300, max: 300).

        Returns:
            str: Presigned WebSocket URL with query string parameters including:
                - Original query params (qualifier, custom_headers)
                - SigV4 auth params (X-Amz-Algorithm, X-Amz-Credential, etc.)

        Raises:
            ValueError: If expires exceeds maximum (300 seconds).
            RuntimeError: If URL generation fails or no credentials found.

        Example:
            >>> client = AgentRuntimeClient('us-west-2')
            >>> presigned_url = client.generate_presigned_url(
            ...     runtime_arn='arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime',
            ...     endpoint_name='DEFAULT',
            ...     custom_headers={'abc': 'pqr'},
            ...     expires=300
            ... )
        """
        self.logger.info("Generating presigned WebSocket URL...")

        # Validate expires parameter
        if expires > MAX_PRESIGNED_URL_TIMEOUT:
            raise ValueError(f"Expiry timeout cannot exceed {MAX_PRESIGNED_URL_TIMEOUT} seconds, got {expires}")

        # Validate ARN
        self._parse_runtime_arn(runtime_arn)

        # Auto-generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            self.logger.debug("Auto-generated session ID: %s", session_id)

        # Build WebSocket URL with query parameters
        ws_url = self._build_websocket_url(runtime_arn, endpoint_name, custom_headers)

        # Convert wss:// to https:// for signing
        https_url = ws_url.replace("wss://", "https://")

        # Parse URL
        url = urlparse(https_url)

        # Get AWS credentials
        credentials = self.session.get_credentials()
        if not credentials:
            raise RuntimeError("No AWS credentials found")

        frozen_credentials = credentials.get_frozen_credentials()

        # Create the request to sign
        request = AWSRequest(method="GET", url=https_url, headers={"host": url.hostname})

        # Sign the request with SigV4QueryAuth
        signer = SigV4QueryAuth(
            credentials=frozen_credentials,
            service_name="bedrock-agentcore",
            region_name=self.region,
            expires=expires,
        )
        signer.add_auth(request)

        if not request.url:
            raise RuntimeError("Failed to generate presigned URL")

        # Convert back to wss:// for WebSocket connection
        presigned_url = request.url.replace("https://", "wss://")

        self.logger.info("✓ Presigned URL generated (expires in %s seconds, Session: %s)", expires, session_id)
        return presigned_url

    def generate_ws_connection_oauth(
        self,
        runtime_arn: str,
        bearer_token: str,
        session_id: Optional[str] = None,
        endpoint_name: Optional[str] = None,
    ) -> Tuple[str, Dict[str, str]]:
        """Generate WebSocket URL and OAuth headers for runtime connection.

        This method uses OAuth bearer token authentication instead of AWS SigV4.
        Suitable for scenarios where OAuth tokens are used for authentication.

        Args:
            runtime_arn (str): Full runtime ARN
                (e.g., 'arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime-abc')
            bearer_token (str): OAuth bearer token for authentication.
            session_id (Optional[str]): Session ID to use. If None, auto-generates one.
            endpoint_name (Optional[str]): Endpoint name to use as 'qualifier' query parameter.
                If provided, adds ?qualifier={endpoint_name} to the URL.

        Returns:
            Tuple[str, Dict[str, str]]: A tuple containing:
                - WebSocket URL (wss://...) with query parameters
                - Headers dictionary with OAuth authentication

        Raises:
            ValueError: If runtime_arn format is invalid or bearer_token is empty.

        Example:
            >>> client = AgentRuntimeClient('us-west-2')
            >>> ws_url, headers = client.generate_ws_connection_oauth(
            ...     runtime_arn='arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime',
            ...     bearer_token='eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...',
            ...     endpoint_name='DEFAULT'
            ... )
        """
        self.logger.info("Generating WebSocket connection with OAuth authentication...")

        # Validate inputs
        if not bearer_token:
            raise ValueError("Bearer token cannot be empty")

        # Validate ARN
        self._parse_runtime_arn(runtime_arn)

        # Auto-generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            self.logger.debug("Auto-generated session ID: %s", session_id)

        # Build WebSocket URL
        ws_url = self._build_websocket_url(runtime_arn, endpoint_name)

        # Convert wss:// to https:// to get host
        https_url = ws_url.replace("wss://", "https://")
        parsed = urlparse(https_url)

        # Generate WebSocket key
        ws_key = base64.b64encode(secrets.token_bytes(16)).decode()

        # Build OAuth headers
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
            "Host": parsed.netloc,
            "Connection": "Upgrade",
            "Upgrade": "websocket",
            "Sec-WebSocket-Key": ws_key,
            "Sec-WebSocket-Version": "13",
            "User-Agent": "OAuth-WebSocket-Client/1.0",
        }

        self.logger.info("✓ OAuth WebSocket connection credentials generated (Session: %s)", session_id)
        self.logger.debug("Bearer token length: %d characters", len(bearer_token))

        return ws_url, headers
```

#### `__init__(region, session=None)`

Initialize an AgentCoreRuntime client for the specified AWS region.

Parameters:

| Name      | Type                | Description                                                                                       | Default    |
| --------- | ------------------- | ------------------------------------------------------------------------------------------------- | ---------- |
| `region`  | `str`               | The AWS region to use for the AgentCore Runtime service.                                          | *required* |
| `session` | `Optional[Session]` | Optional boto3 session. If not provided, a new session will be created using default credentials. | `None`     |

Source code in `bedrock_agentcore/runtime/agent_core_runtime_client.py`

```
def __init__(self, region: str, session: Optional[boto3.Session] = None) -> None:
    """Initialize an AgentCoreRuntime client for the specified AWS region.

    Args:
        region (str): The AWS region to use for the AgentCore Runtime service.
        session (Optional[boto3.Session]): Optional boto3 session. If not provided,
            a new session will be created using default credentials.
    """
    self.region = region
    self.logger = logging.getLogger(__name__)

    if session is None:
        session = boto3.Session()

    self.session = session
```

#### `generate_presigned_url(runtime_arn, session_id=None, endpoint_name=None, custom_headers=None, expires=DEFAULT_PRESIGNED_URL_TIMEOUT)`

Generate a presigned WebSocket URL for runtime connection.

Presigned URLs include authentication in query parameters, allowing frontend clients to connect without managing AWS credentials.

Parameters:

| Name             | Type                       | Description                                                                                                                  | Default                         |
| ---------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------------------------- |
| `runtime_arn`    | `str`                      | Full runtime ARN (e.g., 'arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime-abc')                                    | *required*                      |
| `session_id`     | `Optional[str]`            | Session ID to use. If None, auto-generates a UUID.                                                                           | `None`                          |
| `endpoint_name`  | `Optional[str]`            | Endpoint name to use as 'qualifier' query parameter. If provided, adds ?qualifier={endpoint_name} to the URL before signing. | `None`                          |
| `custom_headers` | `Optional[Dict[str, str]]` | Additional query parameters to include in the presigned URL before signing (e.g., {"abc": "pqr"}).                           | `None`                          |
| `expires`        | `int`                      | Seconds until URL expires (default: 300, max: 300).                                                                          | `DEFAULT_PRESIGNED_URL_TIMEOUT` |

Returns:

| Name  | Type  | Description                                                                                                                                                                       |
| ----- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `str` | `str` | Presigned WebSocket URL with query string parameters including: - Original query params (qualifier, custom_headers) - SigV4 auth params (X-Amz-Algorithm, X-Amz-Credential, etc.) |

Raises:

| Type           | Description                                      |
| -------------- | ------------------------------------------------ |
| `ValueError`   | If expires exceeds maximum (300 seconds).        |
| `RuntimeError` | If URL generation fails or no credentials found. |

Example

> > > client = AgentRuntimeClient('us-west-2') presigned_url = client.generate_presigned_url( ... runtime_arn='arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime', ... endpoint_name='DEFAULT', ... custom_headers={'abc': 'pqr'}, ... expires=300 ... )

Source code in `bedrock_agentcore/runtime/agent_core_runtime_client.py`

```
def generate_presigned_url(
    self,
    runtime_arn: str,
    session_id: Optional[str] = None,
    endpoint_name: Optional[str] = None,
    custom_headers: Optional[Dict[str, str]] = None,
    expires: int = DEFAULT_PRESIGNED_URL_TIMEOUT,
) -> str:
    """Generate a presigned WebSocket URL for runtime connection.

    Presigned URLs include authentication in query parameters, allowing
    frontend clients to connect without managing AWS credentials.

    Args:
        runtime_arn (str): Full runtime ARN
            (e.g., 'arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime-abc')
        session_id (Optional[str]): Session ID to use. If None, auto-generates a UUID.
        endpoint_name (Optional[str]): Endpoint name to use as 'qualifier' query parameter.
            If provided, adds ?qualifier={endpoint_name} to the URL before signing.
        custom_headers (Optional[Dict[str, str]]): Additional query parameters to include
            in the presigned URL before signing (e.g., {"abc": "pqr"}).
        expires (int): Seconds until URL expires (default: 300, max: 300).

    Returns:
        str: Presigned WebSocket URL with query string parameters including:
            - Original query params (qualifier, custom_headers)
            - SigV4 auth params (X-Amz-Algorithm, X-Amz-Credential, etc.)

    Raises:
        ValueError: If expires exceeds maximum (300 seconds).
        RuntimeError: If URL generation fails or no credentials found.

    Example:
        >>> client = AgentRuntimeClient('us-west-2')
        >>> presigned_url = client.generate_presigned_url(
        ...     runtime_arn='arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime',
        ...     endpoint_name='DEFAULT',
        ...     custom_headers={'abc': 'pqr'},
        ...     expires=300
        ... )
    """
    self.logger.info("Generating presigned WebSocket URL...")

    # Validate expires parameter
    if expires > MAX_PRESIGNED_URL_TIMEOUT:
        raise ValueError(f"Expiry timeout cannot exceed {MAX_PRESIGNED_URL_TIMEOUT} seconds, got {expires}")

    # Validate ARN
    self._parse_runtime_arn(runtime_arn)

    # Auto-generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
        self.logger.debug("Auto-generated session ID: %s", session_id)

    # Build WebSocket URL with query parameters
    ws_url = self._build_websocket_url(runtime_arn, endpoint_name, custom_headers)

    # Convert wss:// to https:// for signing
    https_url = ws_url.replace("wss://", "https://")

    # Parse URL
    url = urlparse(https_url)

    # Get AWS credentials
    credentials = self.session.get_credentials()
    if not credentials:
        raise RuntimeError("No AWS credentials found")

    frozen_credentials = credentials.get_frozen_credentials()

    # Create the request to sign
    request = AWSRequest(method="GET", url=https_url, headers={"host": url.hostname})

    # Sign the request with SigV4QueryAuth
    signer = SigV4QueryAuth(
        credentials=frozen_credentials,
        service_name="bedrock-agentcore",
        region_name=self.region,
        expires=expires,
    )
    signer.add_auth(request)

    if not request.url:
        raise RuntimeError("Failed to generate presigned URL")

    # Convert back to wss:// for WebSocket connection
    presigned_url = request.url.replace("https://", "wss://")

    self.logger.info("✓ Presigned URL generated (expires in %s seconds, Session: %s)", expires, session_id)
    return presigned_url
```

#### `generate_ws_connection(runtime_arn, session_id=None, endpoint_name=None)`

Generate WebSocket URL and SigV4 signed headers for runtime connection.

Parameters:

| Name            | Type            | Description                                                                                                   | Default    |
| --------------- | --------------- | ------------------------------------------------------------------------------------------------------------- | ---------- |
| `runtime_arn`   | `str`           | Full runtime ARN (e.g., 'arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime-abc')                     | *required* |
| `session_id`    | `Optional[str]` | Session ID to use. If None, auto-generates a UUID.                                                            | `None`     |
| `endpoint_name` | `Optional[str]` | Endpoint name to use as 'qualifier' query parameter. If provided, adds ?qualifier={endpoint_name} to the URL. | `None`     |

Returns:

| Type                         | Description                                                                                                                                   |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `Tuple[str, Dict[str, str]]` | Tuple\[str, Dict[str, str]\]: A tuple containing: - WebSocket URL (wss://...) with query parameters - Headers dictionary with SigV4 signature |

Raises:

| Type           | Description                       |
| -------------- | --------------------------------- |
| `RuntimeError` | If no AWS credentials are found.  |
| `ValueError`   | If runtime_arn format is invalid. |

Example

> > > client = AgentRuntimeClient('us-west-2') ws_url, headers = client.generate_ws_connection( ... runtime_arn='arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime', ... endpoint_name='DEFAULT' ... )

Source code in `bedrock_agentcore/runtime/agent_core_runtime_client.py`

```
def generate_ws_connection(
    self,
    runtime_arn: str,
    session_id: Optional[str] = None,
    endpoint_name: Optional[str] = None,
) -> Tuple[str, Dict[str, str]]:
    """Generate WebSocket URL and SigV4 signed headers for runtime connection.

    Args:
        runtime_arn (str): Full runtime ARN
            (e.g., 'arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime-abc')
        session_id (Optional[str]): Session ID to use. If None, auto-generates a UUID.
        endpoint_name (Optional[str]): Endpoint name to use as 'qualifier' query parameter.
            If provided, adds ?qualifier={endpoint_name} to the URL.

    Returns:
        Tuple[str, Dict[str, str]]: A tuple containing:
            - WebSocket URL (wss://...) with query parameters
            - Headers dictionary with SigV4 signature

    Raises:
        RuntimeError: If no AWS credentials are found.
        ValueError: If runtime_arn format is invalid.

    Example:
        >>> client = AgentRuntimeClient('us-west-2')
        >>> ws_url, headers = client.generate_ws_connection(
        ...     runtime_arn='arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime',
        ...     endpoint_name='DEFAULT'
        ... )
    """
    self.logger.info("Generating WebSocket connection credentials...")

    # Validate ARN
    self._parse_runtime_arn(runtime_arn)

    # Auto-generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
        self.logger.debug("Auto-generated session ID: %s", session_id)

    # Build WebSocket URL
    ws_url = self._build_websocket_url(runtime_arn, endpoint_name)

    # Get AWS credentials
    credentials = self.session.get_credentials()
    if not credentials:
        raise RuntimeError("No AWS credentials found")

    frozen_credentials = credentials.get_frozen_credentials()

    # Convert wss:// to https:// for signing
    https_url = ws_url.replace("wss://", "https://")
    parsed = urlparse(https_url)
    host = parsed.netloc

    # Create the request to sign
    request = AWSRequest(
        method="GET",
        url=https_url,
        headers={
            "host": host,
            "x-amz-date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        },
    )

    # Sign the request with SigV4
    auth = SigV4Auth(frozen_credentials, "bedrock-agentcore", self.region)
    auth.add_auth(request)

    # Build headers for WebSocket connection
    headers = {
        "Host": host,
        "X-Amz-Date": request.headers["x-amz-date"],
        "Authorization": request.headers["Authorization"],
        "Upgrade": "websocket",
        "Connection": "Upgrade",
        "Sec-WebSocket-Version": "13",
        "Sec-WebSocket-Key": base64.b64encode(secrets.token_bytes(16)).decode(),
        "User-Agent": f"AgentRuntime-Client/1.0 (Session: {session_id})",
    }

    # Add session token if present
    if frozen_credentials.token:
        headers["X-Amz-Security-Token"] = frozen_credentials.token

    self.logger.info("✓ WebSocket connection credentials generated (Session: %s)", session_id)
    return ws_url, headers
```

#### `generate_ws_connection_oauth(runtime_arn, bearer_token, session_id=None, endpoint_name=None)`

Generate WebSocket URL and OAuth headers for runtime connection.

This method uses OAuth bearer token authentication instead of AWS SigV4. Suitable for scenarios where OAuth tokens are used for authentication.

Parameters:

| Name            | Type            | Description                                                                                                   | Default    |
| --------------- | --------------- | ------------------------------------------------------------------------------------------------------------- | ---------- |
| `runtime_arn`   | `str`           | Full runtime ARN (e.g., 'arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime-abc')                     | *required* |
| `bearer_token`  | `str`           | OAuth bearer token for authentication.                                                                        | *required* |
| `session_id`    | `Optional[str]` | Session ID to use. If None, auto-generates one.                                                               | `None`     |
| `endpoint_name` | `Optional[str]` | Endpoint name to use as 'qualifier' query parameter. If provided, adds ?qualifier={endpoint_name} to the URL. | `None`     |

Returns:

| Type                         | Description                                                                                                                                        |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Tuple[str, Dict[str, str]]` | Tuple\[str, Dict[str, str]\]: A tuple containing: - WebSocket URL (wss://...) with query parameters - Headers dictionary with OAuth authentication |

Raises:

| Type         | Description                                                |
| ------------ | ---------------------------------------------------------- |
| `ValueError` | If runtime_arn format is invalid or bearer_token is empty. |

Example

> > > client = AgentRuntimeClient('us-west-2') ws_url, headers = client.generate_ws_connection_oauth( ... runtime_arn='arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime', ... bearer_token='eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...', ... endpoint_name='DEFAULT' ... )

Source code in `bedrock_agentcore/runtime/agent_core_runtime_client.py`

```
def generate_ws_connection_oauth(
    self,
    runtime_arn: str,
    bearer_token: str,
    session_id: Optional[str] = None,
    endpoint_name: Optional[str] = None,
) -> Tuple[str, Dict[str, str]]:
    """Generate WebSocket URL and OAuth headers for runtime connection.

    This method uses OAuth bearer token authentication instead of AWS SigV4.
    Suitable for scenarios where OAuth tokens are used for authentication.

    Args:
        runtime_arn (str): Full runtime ARN
            (e.g., 'arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime-abc')
        bearer_token (str): OAuth bearer token for authentication.
        session_id (Optional[str]): Session ID to use. If None, auto-generates one.
        endpoint_name (Optional[str]): Endpoint name to use as 'qualifier' query parameter.
            If provided, adds ?qualifier={endpoint_name} to the URL.

    Returns:
        Tuple[str, Dict[str, str]]: A tuple containing:
            - WebSocket URL (wss://...) with query parameters
            - Headers dictionary with OAuth authentication

    Raises:
        ValueError: If runtime_arn format is invalid or bearer_token is empty.

    Example:
        >>> client = AgentRuntimeClient('us-west-2')
        >>> ws_url, headers = client.generate_ws_connection_oauth(
        ...     runtime_arn='arn:aws:bedrock-agentcore:us-west-2:123:runtime/my-runtime',
        ...     bearer_token='eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...',
        ...     endpoint_name='DEFAULT'
        ... )
    """
    self.logger.info("Generating WebSocket connection with OAuth authentication...")

    # Validate inputs
    if not bearer_token:
        raise ValueError("Bearer token cannot be empty")

    # Validate ARN
    self._parse_runtime_arn(runtime_arn)

    # Auto-generate session ID if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
        self.logger.debug("Auto-generated session ID: %s", session_id)

    # Build WebSocket URL
    ws_url = self._build_websocket_url(runtime_arn, endpoint_name)

    # Convert wss:// to https:// to get host
    https_url = ws_url.replace("wss://", "https://")
    parsed = urlparse(https_url)

    # Generate WebSocket key
    ws_key = base64.b64encode(secrets.token_bytes(16)).decode()

    # Build OAuth headers
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
        "Host": parsed.netloc,
        "Connection": "Upgrade",
        "Upgrade": "websocket",
        "Sec-WebSocket-Key": ws_key,
        "Sec-WebSocket-Version": "13",
        "User-Agent": "OAuth-WebSocket-Client/1.0",
    }

    self.logger.info("✓ OAuth WebSocket connection credentials generated (Session: %s)", session_id)
    self.logger.debug("Bearer token length: %d characters", len(bearer_token))

    return ws_url, headers
```

### `BedrockAgentCoreApp`

Bases: `Starlette`

Bedrock AgentCore application class that extends Starlette for AI agent deployment.

Source code in `bedrock_agentcore/runtime/app.py`

```
class BedrockAgentCoreApp(Starlette):
    """Bedrock AgentCore application class that extends Starlette for AI agent deployment."""

    def __init__(
        self,
        debug: bool = False,
        lifespan: Optional[Lifespan] = None,
        middleware: Sequence[Middleware] | None = None,
    ):
        """Initialize Bedrock AgentCore application.

        Args:
            debug: Enable debug actions for task management (default: False)
            lifespan: Optional lifespan context manager for startup/shutdown
            middleware: Optional sequence of Starlette Middleware objects (or Middleware(...) entries)
        """
        self.handlers: Dict[str, Callable] = {}
        self._ping_handler: Optional[Callable] = None
        self._websocket_handler: Optional[Callable] = None
        self._active_tasks: Dict[int, Dict[str, Any]] = {}
        self._task_counter_lock: threading.Lock = threading.Lock()
        self._forced_ping_status: Optional[PingStatus] = None
        self._last_status_update_time: float = time.time()

        routes = [
            Route("/invocations", self._handle_invocation, methods=["POST"]),
            Route("/ping", self._handle_ping, methods=["GET"]),
            WebSocketRoute("/ws", self._handle_websocket),
        ]
        super().__init__(routes=routes, lifespan=lifespan, middleware=middleware)
        self.debug = debug  # Set after super().__init__ to avoid override

        self.logger = logging.getLogger("bedrock_agentcore.app")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = RequestContextFormatter()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)

    def entrypoint(self, func: Callable) -> Callable:
        """Decorator to register a function as the main entrypoint.

        Args:
            func: The function to register as entrypoint

        Returns:
            The decorated function with added serve method
        """
        self.handlers["main"] = func
        func.run = lambda port=8080, host=None: self.run(port, host)
        return func

    def ping(self, func: Callable) -> Callable:
        """Decorator to register a custom ping status handler.

        Args:
            func: The function to register as ping status handler

        Returns:
            The decorated function
        """
        self._ping_handler = func
        return func

    def websocket(self, func: Callable) -> Callable:
        """Decorator to register a WebSocket handler at /ws endpoint.

        Args:
            func: The function to register as WebSocket handler

        Returns:
            The decorated function

        Example:
            @app.websocket
            async def handler(websocket, context):
                await websocket.accept()
                # ... handle messages ...
        """
        self._websocket_handler = func
        return func

    def async_task(self, func: Callable) -> Callable:
        """Decorator to track async tasks for ping status.

        When a function is decorated with @async_task, it will:
        - Set ping status to HEALTHY_BUSY while running
        - Revert to HEALTHY when complete
        """
        if not asyncio.iscoroutinefunction(func):
            raise ValueError("@async_task can only be applied to async functions")

        async def wrapper(*args, **kwargs):
            task_id = self.add_async_task(func.__name__)

            try:
                self.logger.debug("Starting async task: %s", func.__name__)
                start_time = time.time()
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                self.logger.info("Async task completed: %s (%.3fs)", func.__name__, duration)
                return result
            except Exception:
                duration = time.time() - start_time
                self.logger.exception("Async task failed: %s (%.3fs)", func.__name__, duration)
                raise
            finally:
                self.complete_async_task(task_id)

        wrapper.__name__ = func.__name__
        return wrapper

    def get_current_ping_status(self) -> PingStatus:
        """Get current ping status (forced > custom > automatic)."""
        current_status = None

        if self._forced_ping_status is not None:
            current_status = self._forced_ping_status
        elif self._ping_handler:
            try:
                result = self._ping_handler()
                if isinstance(result, str):
                    current_status = PingStatus(result)
                else:
                    current_status = result
            except Exception as e:
                self.logger.warning(
                    "Custom ping handler failed, falling back to automatic: %s: %s", type(e).__name__, e
                )

        if current_status is None:
            current_status = PingStatus.HEALTHY_BUSY if self._active_tasks else PingStatus.HEALTHY
        if not hasattr(self, "_last_known_status") or self._last_known_status != current_status:
            self._last_known_status = current_status
            self._last_status_update_time = time.time()

        return current_status

    def force_ping_status(self, status: PingStatus):
        """Force ping status to a specific value."""
        self._forced_ping_status = status

    def clear_forced_ping_status(self):
        """Clear forced status and resume automatic."""
        self._forced_ping_status = None

    def get_async_task_info(self) -> Dict[str, Any]:
        """Get info about running async tasks."""
        running_jobs = []
        for t in self._active_tasks.values():
            try:
                running_jobs.append(
                    {"name": t.get("name", "unknown"), "duration": time.time() - t.get("start_time", time.time())}
                )
            except Exception as e:
                self.logger.warning("Caught exception, continuing...: %s", e)
                continue

        return {"active_count": len(self._active_tasks), "running_jobs": running_jobs}

    def add_async_task(self, name: str, metadata: Optional[Dict] = None) -> int:
        """Register an async task for interactive health tracking.

        This method provides granular control over async task lifecycle,
        allowing developers to interactively start tracking tasks for health monitoring.
        Use this when you need precise control over when tasks begin and end.

        Args:
            name: Human-readable task name for monitoring
            metadata: Optional additional task metadata

        Returns:
            Task ID for tracking and completion

        Example:
            task_id = app.add_async_task("file_processing", {"file": "data.csv"})
            # ... do background work ...
            app.complete_async_task(task_id)
        """
        with self._task_counter_lock:
            task_id = hash(str(uuid.uuid4()))  # Generate truly unique hash-based ID

            # Register task start with same structure as @async_task decorator
            task_info = {"name": name, "start_time": time.time()}
            if metadata:
                task_info["metadata"] = metadata

            self._active_tasks[task_id] = task_info

        self.logger.info("Async task started: %s (ID: %s)", name, task_id)
        return task_id

    def complete_async_task(self, task_id: int) -> bool:
        """Mark an async task as complete for interactive health tracking.

        This method provides granular control over async task lifecycle,
        allowing developers to interactively complete tasks for health monitoring.
        Call this when your background work finishes.

        Args:
            task_id: Task ID returned from add_async_task

        Returns:
            True if task was found and completed, False otherwise

        Example:
            task_id = app.add_async_task("file_processing")
            # ... do background work ...
            completed = app.complete_async_task(task_id)
        """
        with self._task_counter_lock:
            task_info = self._active_tasks.pop(task_id, None)
            if task_info:
                task_name = task_info.get("name", "unknown")
                duration = time.time() - task_info.get("start_time", time.time())

                self.logger.info("Async task completed: %s (ID: %s, Duration: %.2fs)", task_name, task_id, duration)
                return True
            else:
                self.logger.warning("Attempted to complete unknown task ID: %s", task_id)
                return False

    def _build_request_context(self, request) -> RequestContext:
        """Build request context and setup all context variables."""
        try:
            headers = request.headers
            request_id = headers.get(REQUEST_ID_HEADER)
            if not request_id:
                request_id = str(uuid.uuid4())

            session_id = headers.get(SESSION_HEADER)
            BedrockAgentCoreContext.set_request_context(request_id, session_id)

            agent_identity_token = headers.get(ACCESS_TOKEN_HEADER)
            if agent_identity_token:
                BedrockAgentCoreContext.set_workload_access_token(agent_identity_token)

            oauth2_callback_url = headers.get(OAUTH2_CALLBACK_URL_HEADER)
            if oauth2_callback_url:
                BedrockAgentCoreContext.set_oauth2_callback_url(oauth2_callback_url)

            # Collect relevant request headers (Authorization + Custom headers)
            request_headers = {}

            # Add Authorization header if present
            authorization_header = headers.get(AUTHORIZATION_HEADER)
            if authorization_header is not None:
                request_headers[AUTHORIZATION_HEADER] = authorization_header

            # Add custom headers with the specified prefix
            for header_name, header_value in headers.items():
                if header_name.lower().startswith(CUSTOM_HEADER_PREFIX.lower()):
                    request_headers[header_name] = header_value

            # Set in context if any headers were found
            if request_headers:
                BedrockAgentCoreContext.set_request_headers(request_headers)

            # Get the headers from context to pass to RequestContext
            req_headers = BedrockAgentCoreContext.get_request_headers()

            return RequestContext(
                session_id=session_id,
                request_headers=req_headers,
                request=request,  # Pass through the Starlette request object
            )
        except Exception as e:
            self.logger.warning("Failed to build request context: %s: %s", type(e).__name__, e)
            request_id = str(uuid.uuid4())
            BedrockAgentCoreContext.set_request_context(request_id, None)
            return RequestContext(session_id=None, request=None)

    def _takes_context(self, handler: Callable) -> bool:
        try:
            params = list(inspect.signature(handler).parameters.keys())
            return len(params) >= 2 and params[1] == "context"
        except Exception:
            return False

    async def _handle_invocation(self, request):
        request_context = self._build_request_context(request)

        start_time = time.time()

        try:
            payload = await request.json()
            self.logger.debug("Processing invocation request")

            if self.debug:
                task_response = self._handle_task_action(payload)
                if task_response:
                    duration = time.time() - start_time
                    self.logger.info("Debug action completed (%.3fs)", duration)
                    return task_response

            handler = self.handlers.get("main")
            if not handler:
                self.logger.error("No entrypoint defined")
                return JSONResponse({"error": "No entrypoint defined"}, status_code=500)

            takes_context = self._takes_context(handler)

            handler_name = handler.__name__ if hasattr(handler, "__name__") else "unknown"
            self.logger.debug("Invoking handler: %s", handler_name)
            result = await self._invoke_handler(handler, request_context, takes_context, payload)

            duration = time.time() - start_time
            if inspect.isgenerator(result):
                self.logger.info("Returning streaming response (generator) (%.3fs)", duration)
                return StreamingResponse(self._sync_stream_with_error_handling(result), media_type="text/event-stream")
            elif inspect.isasyncgen(result):
                self.logger.info("Returning streaming response (async generator) (%.3fs)", duration)
                return StreamingResponse(self._stream_with_error_handling(result), media_type="text/event-stream")

            self.logger.info("Invocation completed successfully (%.3fs)", duration)
            # Use safe serialization for consistency with streaming paths
            safe_json_string = self._safe_serialize_to_json_string(result)
            return Response(safe_json_string, media_type="application/json")

        except json.JSONDecodeError as e:
            duration = time.time() - start_time
            self.logger.warning("Invalid JSON in request (%.3fs): %s", duration, e)
            return JSONResponse({"error": "Invalid JSON", "details": str(e)}, status_code=400)
        except Exception as e:
            duration = time.time() - start_time
            self.logger.exception("Invocation failed (%.3fs)", duration)
            return JSONResponse({"error": str(e)}, status_code=500)

    def _handle_ping(self, request):
        try:
            status = self.get_current_ping_status()
            self.logger.debug("Ping request - status: %s", status.value)
            return JSONResponse({"status": status.value, "time_of_last_update": int(self._last_status_update_time)})
        except Exception:
            self.logger.exception("Ping endpoint failed")
            return JSONResponse({"status": PingStatus.HEALTHY.value, "time_of_last_update": int(time.time())})

    async def _handle_websocket(self, websocket: WebSocket):
        """Handle WebSocket connections."""
        request_context = self._build_request_context(websocket)

        try:
            handler = self._websocket_handler
            if not handler:
                self.logger.error("No WebSocket handler defined")
                await websocket.close(code=1011)
                return

            self.logger.debug("WebSocket connection established")
            await handler(websocket, request_context)

        except WebSocketDisconnect:
            self.logger.debug("WebSocket disconnected")
        except Exception:
            self.logger.exception("WebSocket handler failed")
            try:
                await websocket.close(code=1011)
            except Exception:
                pass

    def run(self, port: int = 8080, host: Optional[str] = None, **kwargs):
        """Start the Bedrock AgentCore server.

        Args:
            port: Port to serve on, defaults to 8080
            host: Host to bind to, auto-detected if None
            **kwargs: Additional arguments passed to uvicorn.run()
        """
        import os

        import uvicorn

        if host is None:
            if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER"):
                host = "0.0.0.0"  # nosec B104 - Docker needs this to expose the port
            else:
                host = "127.0.0.1"

        # Set default uvicorn parameters, allow kwargs to override
        uvicorn_params = {
            "host": host,
            "port": port,
            "access_log": self.debug,
            "log_level": "info" if self.debug else "warning",
        }
        uvicorn_params.update(kwargs)

        uvicorn.run(self, **uvicorn_params)

    async def _invoke_handler(self, handler, request_context, takes_context, payload):
        try:
            args = (payload, request_context) if takes_context else (payload,)

            if asyncio.iscoroutinefunction(handler):
                return await handler(*args)
            else:
                loop = asyncio.get_event_loop()
                ctx = contextvars.copy_context()
                return await loop.run_in_executor(None, ctx.run, handler, *args)
        except Exception:
            handler_name = getattr(handler, "__name__", "unknown")
            self.logger.debug("Handler '%s' execution failed", handler_name)
            raise

    def _handle_task_action(self, payload: dict) -> Optional[JSONResponse]:
        """Handle task management actions if present in payload."""
        action = payload.get("_agent_core_app_action")
        if not action:
            return None

        self.logger.debug("Processing debug action: %s", action)

        try:
            actions = {
                TASK_ACTION_PING_STATUS: lambda: JSONResponse(
                    {
                        "status": self.get_current_ping_status().value,
                        "time_of_last_update": int(self._last_status_update_time),
                    }
                ),
                TASK_ACTION_JOB_STATUS: lambda: JSONResponse(self.get_async_task_info()),
                TASK_ACTION_FORCE_HEALTHY: lambda: (
                    self.force_ping_status(PingStatus.HEALTHY),
                    self.logger.info("Ping status forced to Healthy"),
                    JSONResponse({"forced_status": "Healthy"}),
                )[2],
                TASK_ACTION_FORCE_BUSY: lambda: (
                    self.force_ping_status(PingStatus.HEALTHY_BUSY),
                    self.logger.info("Ping status forced to HealthyBusy"),
                    JSONResponse({"forced_status": "HealthyBusy"}),
                )[2],
                TASK_ACTION_CLEAR_FORCED_STATUS: lambda: (
                    self.clear_forced_ping_status(),
                    self.logger.info("Forced ping status cleared"),
                    JSONResponse({"forced_status": "Cleared"}),
                )[2],
            }

            if action in actions:
                response = actions[action]()
                self.logger.debug("Debug action '%s' completed successfully", action)
                return response

            self.logger.warning("Unknown debug action requested: %s", action)
            return JSONResponse({"error": f"Unknown action: {action}"}, status_code=400)

        except Exception as e:
            self.logger.exception("Debug action '%s' failed", action)
            return JSONResponse({"error": "Debug action failed", "details": str(e)}, status_code=500)

    async def _stream_with_error_handling(self, generator):
        """Wrap async generator to handle errors and convert to SSE format."""
        try:
            async for value in generator:
                yield self._convert_to_sse(value)
        except Exception as e:
            self.logger.exception("Error in async streaming")
            error_event = {
                "error": str(e),
                "error_type": type(e).__name__,
                "message": "An error occurred during streaming",
            }
            yield self._convert_to_sse(error_event)

    def _safe_serialize_to_json_string(self, obj):
        """Safely serialize object directly to JSON string with progressive fallback handling.

        This method eliminates double JSON encoding by returning the JSON string directly,
        avoiding the test-then-encode pattern that leads to redundant json.dumps() calls.
        Used by both streaming and non-streaming responses for consistent behavior.

        Returns:
            str: JSON string representation of the object
        """
        try:
            # First attempt: direct JSON serialization with Unicode support
            return json.dumps(obj, ensure_ascii=False)
        except (TypeError, ValueError, UnicodeEncodeError):
            try:
                # Second attempt: convert to serializable dictionaries, then JSON encode the dictionaries
                converted_obj = convert_complex_objects(obj)
                return json.dumps(converted_obj, ensure_ascii=False)
            except Exception:
                try:
                    # Third attempt: convert to string, then JSON encode the string
                    return json.dumps(str(obj), ensure_ascii=False)
                except Exception as e:
                    # Final fallback: JSON encode error object with ASCII fallback for problematic Unicode
                    self.logger.warning("Failed to serialize object: %s: %s", type(e).__name__, e)
                    error_obj = {"error": "Serialization failed", "original_type": type(obj).__name__}
                    return json.dumps(error_obj, ensure_ascii=False)

    def _convert_to_sse(self, obj) -> bytes:
        """Convert object to Server-Sent Events format using safe serialization.

        Args:
            obj: Object to convert to SSE format

        Returns:
            bytes: SSE-formatted data ready for streaming
        """
        json_string = self._safe_serialize_to_json_string(obj)
        sse_data = f"data: {json_string}\n\n"
        return sse_data.encode("utf-8")

    def _sync_stream_with_error_handling(self, generator):
        """Wrap sync generator to handle errors and convert to SSE format."""
        try:
            for value in generator:
                yield self._convert_to_sse(value)
        except Exception as e:
            self.logger.exception("Error in sync streaming")
            error_event = {
                "error": str(e),
                "error_type": type(e).__name__,
                "message": "An error occurred during streaming",
            }
            yield self._convert_to_sse(error_event)
```

#### `__init__(debug=False, lifespan=None, middleware=None)`

Initialize Bedrock AgentCore application.

Parameters:

| Name         | Type                   | Description                                               | Default                                                                        |
| ------------ | ---------------------- | --------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `debug`      | `bool`                 | Enable debug actions for task management (default: False) | `False`                                                                        |
| `lifespan`   | `Optional[Lifespan]`   | Optional lifespan context manager for startup/shutdown    | `None`                                                                         |
| `middleware` | \`Sequence[Middleware] | None\`                                                    | Optional sequence of Starlette Middleware objects (or Middleware(...) entries) |

Source code in `bedrock_agentcore/runtime/app.py`

```
def __init__(
    self,
    debug: bool = False,
    lifespan: Optional[Lifespan] = None,
    middleware: Sequence[Middleware] | None = None,
):
    """Initialize Bedrock AgentCore application.

    Args:
        debug: Enable debug actions for task management (default: False)
        lifespan: Optional lifespan context manager for startup/shutdown
        middleware: Optional sequence of Starlette Middleware objects (or Middleware(...) entries)
    """
    self.handlers: Dict[str, Callable] = {}
    self._ping_handler: Optional[Callable] = None
    self._websocket_handler: Optional[Callable] = None
    self._active_tasks: Dict[int, Dict[str, Any]] = {}
    self._task_counter_lock: threading.Lock = threading.Lock()
    self._forced_ping_status: Optional[PingStatus] = None
    self._last_status_update_time: float = time.time()

    routes = [
        Route("/invocations", self._handle_invocation, methods=["POST"]),
        Route("/ping", self._handle_ping, methods=["GET"]),
        WebSocketRoute("/ws", self._handle_websocket),
    ]
    super().__init__(routes=routes, lifespan=lifespan, middleware=middleware)
    self.debug = debug  # Set after super().__init__ to avoid override

    self.logger = logging.getLogger("bedrock_agentcore.app")
    if not self.logger.handlers:
        handler = logging.StreamHandler()
        formatter = RequestContextFormatter()
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG if self.debug else logging.INFO)
```

#### `add_async_task(name, metadata=None)`

Register an async task for interactive health tracking.

This method provides granular control over async task lifecycle, allowing developers to interactively start tracking tasks for health monitoring. Use this when you need precise control over when tasks begin and end.

Parameters:

| Name       | Type             | Description                             | Default    |
| ---------- | ---------------- | --------------------------------------- | ---------- |
| `name`     | `str`            | Human-readable task name for monitoring | *required* |
| `metadata` | `Optional[Dict]` | Optional additional task metadata       | `None`     |

Returns:

| Type  | Description                         |
| ----- | ----------------------------------- |
| `int` | Task ID for tracking and completion |

Example

task_id = app.add_async_task("file_processing", {"file": "data.csv"})

##### ... do background work ...

app.complete_async_task(task_id)

Source code in `bedrock_agentcore/runtime/app.py`

```
def add_async_task(self, name: str, metadata: Optional[Dict] = None) -> int:
    """Register an async task for interactive health tracking.

    This method provides granular control over async task lifecycle,
    allowing developers to interactively start tracking tasks for health monitoring.
    Use this when you need precise control over when tasks begin and end.

    Args:
        name: Human-readable task name for monitoring
        metadata: Optional additional task metadata

    Returns:
        Task ID for tracking and completion

    Example:
        task_id = app.add_async_task("file_processing", {"file": "data.csv"})
        # ... do background work ...
        app.complete_async_task(task_id)
    """
    with self._task_counter_lock:
        task_id = hash(str(uuid.uuid4()))  # Generate truly unique hash-based ID

        # Register task start with same structure as @async_task decorator
        task_info = {"name": name, "start_time": time.time()}
        if metadata:
            task_info["metadata"] = metadata

        self._active_tasks[task_id] = task_info

    self.logger.info("Async task started: %s (ID: %s)", name, task_id)
    return task_id
```

#### `async_task(func)`

Decorator to track async tasks for ping status.

When a function is decorated with @async_task, it will:

- Set ping status to HEALTHY_BUSY while running
- Revert to HEALTHY when complete

Source code in `bedrock_agentcore/runtime/app.py`

```
def async_task(self, func: Callable) -> Callable:
    """Decorator to track async tasks for ping status.

    When a function is decorated with @async_task, it will:
    - Set ping status to HEALTHY_BUSY while running
    - Revert to HEALTHY when complete
    """
    if not asyncio.iscoroutinefunction(func):
        raise ValueError("@async_task can only be applied to async functions")

    async def wrapper(*args, **kwargs):
        task_id = self.add_async_task(func.__name__)

        try:
            self.logger.debug("Starting async task: %s", func.__name__)
            start_time = time.time()
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            self.logger.info("Async task completed: %s (%.3fs)", func.__name__, duration)
            return result
        except Exception:
            duration = time.time() - start_time
            self.logger.exception("Async task failed: %s (%.3fs)", func.__name__, duration)
            raise
        finally:
            self.complete_async_task(task_id)

    wrapper.__name__ = func.__name__
    return wrapper
```

#### `clear_forced_ping_status()`

Clear forced status and resume automatic.

Source code in `bedrock_agentcore/runtime/app.py`

```
def clear_forced_ping_status(self):
    """Clear forced status and resume automatic."""
    self._forced_ping_status = None
```

#### `complete_async_task(task_id)`

Mark an async task as complete for interactive health tracking.

This method provides granular control over async task lifecycle, allowing developers to interactively complete tasks for health monitoring. Call this when your background work finishes.

Parameters:

| Name      | Type  | Description                          | Default    |
| --------- | ----- | ------------------------------------ | ---------- |
| `task_id` | `int` | Task ID returned from add_async_task | *required* |

Returns:

| Type   | Description                                           |
| ------ | ----------------------------------------------------- |
| `bool` | True if task was found and completed, False otherwise |

Example

task_id = app.add_async_task("file_processing")

##### ... do background work ...

completed = app.complete_async_task(task_id)

Source code in `bedrock_agentcore/runtime/app.py`

```
def complete_async_task(self, task_id: int) -> bool:
    """Mark an async task as complete for interactive health tracking.

    This method provides granular control over async task lifecycle,
    allowing developers to interactively complete tasks for health monitoring.
    Call this when your background work finishes.

    Args:
        task_id: Task ID returned from add_async_task

    Returns:
        True if task was found and completed, False otherwise

    Example:
        task_id = app.add_async_task("file_processing")
        # ... do background work ...
        completed = app.complete_async_task(task_id)
    """
    with self._task_counter_lock:
        task_info = self._active_tasks.pop(task_id, None)
        if task_info:
            task_name = task_info.get("name", "unknown")
            duration = time.time() - task_info.get("start_time", time.time())

            self.logger.info("Async task completed: %s (ID: %s, Duration: %.2fs)", task_name, task_id, duration)
            return True
        else:
            self.logger.warning("Attempted to complete unknown task ID: %s", task_id)
            return False
```

#### `entrypoint(func)`

Decorator to register a function as the main entrypoint.

Parameters:

| Name   | Type       | Description                            | Default    |
| ------ | ---------- | -------------------------------------- | ---------- |
| `func` | `Callable` | The function to register as entrypoint | *required* |

Returns:

| Type       | Description                                    |
| ---------- | ---------------------------------------------- |
| `Callable` | The decorated function with added serve method |

Source code in `bedrock_agentcore/runtime/app.py`

```
def entrypoint(self, func: Callable) -> Callable:
    """Decorator to register a function as the main entrypoint.

    Args:
        func: The function to register as entrypoint

    Returns:
        The decorated function with added serve method
    """
    self.handlers["main"] = func
    func.run = lambda port=8080, host=None: self.run(port, host)
    return func
```

#### `force_ping_status(status)`

Force ping status to a specific value.

Source code in `bedrock_agentcore/runtime/app.py`

```
def force_ping_status(self, status: PingStatus):
    """Force ping status to a specific value."""
    self._forced_ping_status = status
```

#### `get_async_task_info()`

Get info about running async tasks.

Source code in `bedrock_agentcore/runtime/app.py`

```
def get_async_task_info(self) -> Dict[str, Any]:
    """Get info about running async tasks."""
    running_jobs = []
    for t in self._active_tasks.values():
        try:
            running_jobs.append(
                {"name": t.get("name", "unknown"), "duration": time.time() - t.get("start_time", time.time())}
            )
        except Exception as e:
            self.logger.warning("Caught exception, continuing...: %s", e)
            continue

    return {"active_count": len(self._active_tasks), "running_jobs": running_jobs}
```

#### `get_current_ping_status()`

Get current ping status (forced > custom > automatic).

Source code in `bedrock_agentcore/runtime/app.py`

```
def get_current_ping_status(self) -> PingStatus:
    """Get current ping status (forced > custom > automatic)."""
    current_status = None

    if self._forced_ping_status is not None:
        current_status = self._forced_ping_status
    elif self._ping_handler:
        try:
            result = self._ping_handler()
            if isinstance(result, str):
                current_status = PingStatus(result)
            else:
                current_status = result
        except Exception as e:
            self.logger.warning(
                "Custom ping handler failed, falling back to automatic: %s: %s", type(e).__name__, e
            )

    if current_status is None:
        current_status = PingStatus.HEALTHY_BUSY if self._active_tasks else PingStatus.HEALTHY
    if not hasattr(self, "_last_known_status") or self._last_known_status != current_status:
        self._last_known_status = current_status
        self._last_status_update_time = time.time()

    return current_status
```

#### `ping(func)`

Decorator to register a custom ping status handler.

Parameters:

| Name   | Type       | Description                                     | Default    |
| ------ | ---------- | ----------------------------------------------- | ---------- |
| `func` | `Callable` | The function to register as ping status handler | *required* |

Returns:

| Type       | Description            |
| ---------- | ---------------------- |
| `Callable` | The decorated function |

Source code in `bedrock_agentcore/runtime/app.py`

```
def ping(self, func: Callable) -> Callable:
    """Decorator to register a custom ping status handler.

    Args:
        func: The function to register as ping status handler

    Returns:
        The decorated function
    """
    self._ping_handler = func
    return func
```

#### `run(port=8080, host=None, **kwargs)`

Start the Bedrock AgentCore server.

Parameters:

| Name       | Type            | Description                                  | Default |
| ---------- | --------------- | -------------------------------------------- | ------- |
| `port`     | `int`           | Port to serve on, defaults to 8080           | `8080`  |
| `host`     | `Optional[str]` | Host to bind to, auto-detected if None       | `None`  |
| `**kwargs` |                 | Additional arguments passed to uvicorn.run() | `{}`    |

Source code in `bedrock_agentcore/runtime/app.py`

```
def run(self, port: int = 8080, host: Optional[str] = None, **kwargs):
    """Start the Bedrock AgentCore server.

    Args:
        port: Port to serve on, defaults to 8080
        host: Host to bind to, auto-detected if None
        **kwargs: Additional arguments passed to uvicorn.run()
    """
    import os

    import uvicorn

    if host is None:
        if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER"):
            host = "0.0.0.0"  # nosec B104 - Docker needs this to expose the port
        else:
            host = "127.0.0.1"

    # Set default uvicorn parameters, allow kwargs to override
    uvicorn_params = {
        "host": host,
        "port": port,
        "access_log": self.debug,
        "log_level": "info" if self.debug else "warning",
    }
    uvicorn_params.update(kwargs)

    uvicorn.run(self, **uvicorn_params)
```

#### `websocket(func)`

Decorator to register a WebSocket handler at /ws endpoint.

Parameters:

| Name   | Type       | Description                                   | Default    |
| ------ | ---------- | --------------------------------------------- | ---------- |
| `func` | `Callable` | The function to register as WebSocket handler | *required* |

Returns:

| Type       | Description            |
| ---------- | ---------------------- |
| `Callable` | The decorated function |

Example

@app.websocket async def handler(websocket, context): await websocket.accept()

# ... handle messages ...

Source code in `bedrock_agentcore/runtime/app.py`

```
def websocket(self, func: Callable) -> Callable:
    """Decorator to register a WebSocket handler at /ws endpoint.

    Args:
        func: The function to register as WebSocket handler

    Returns:
        The decorated function

    Example:
        @app.websocket
        async def handler(websocket, context):
            await websocket.accept()
            # ... handle messages ...
    """
    self._websocket_handler = func
    return func
```

### `BedrockAgentCoreContext`

Unified context manager for Bedrock AgentCore.

Source code in `bedrock_agentcore/runtime/context.py`

```
class BedrockAgentCoreContext:
    """Unified context manager for Bedrock AgentCore."""

    _workload_access_token: ContextVar[Optional[str]] = ContextVar("workload_access_token")
    _oauth2_callback_url: ContextVar[Optional[str]] = ContextVar("oauth2_callback_url")
    _request_id: ContextVar[Optional[str]] = ContextVar("request_id")
    _session_id: ContextVar[Optional[str]] = ContextVar("session_id")
    _request_headers: ContextVar[Optional[Dict[str, str]]] = ContextVar("request_headers")

    @classmethod
    def set_workload_access_token(cls, token: str):
        """Set the workload access token in the context."""
        cls._workload_access_token.set(token)

    @classmethod
    def get_workload_access_token(cls) -> Optional[str]:
        """Get the workload access token from the context."""
        try:
            return cls._workload_access_token.get()
        except LookupError:
            return None

    @classmethod
    def set_oauth2_callback_url(cls, workload_callback_url: str):
        """Set the oauth2 callback url in the context."""
        cls._oauth2_callback_url.set(workload_callback_url)

    @classmethod
    def get_oauth2_callback_url(cls) -> Optional[str]:
        """Get the oauth2 callback url from the context."""
        try:
            return cls._oauth2_callback_url.get()
        except LookupError:
            return None

    @classmethod
    def set_request_context(cls, request_id: str, session_id: Optional[str] = None):
        """Set request-scoped identifiers."""
        cls._request_id.set(request_id)
        cls._session_id.set(session_id)

    @classmethod
    def get_request_id(cls) -> Optional[str]:
        """Get current request ID."""
        try:
            return cls._request_id.get()
        except LookupError:
            return None

    @classmethod
    def get_session_id(cls) -> Optional[str]:
        """Get current session ID."""
        try:
            return cls._session_id.get()
        except LookupError:
            return None

    @classmethod
    def set_request_headers(cls, headers: Dict[str, str]):
        """Set request headers in the context."""
        cls._request_headers.set(headers)

    @classmethod
    def get_request_headers(cls) -> Optional[Dict[str, str]]:
        """Get request headers from the context."""
        try:
            return cls._request_headers.get()
        except LookupError:
            return None
```

#### `get_oauth2_callback_url()`

Get the oauth2 callback url from the context.

Source code in `bedrock_agentcore/runtime/context.py`

```
@classmethod
def get_oauth2_callback_url(cls) -> Optional[str]:
    """Get the oauth2 callback url from the context."""
    try:
        return cls._oauth2_callback_url.get()
    except LookupError:
        return None
```

#### `get_request_headers()`

Get request headers from the context.

Source code in `bedrock_agentcore/runtime/context.py`

```
@classmethod
def get_request_headers(cls) -> Optional[Dict[str, str]]:
    """Get request headers from the context."""
    try:
        return cls._request_headers.get()
    except LookupError:
        return None
```

#### `get_request_id()`

Get current request ID.

Source code in `bedrock_agentcore/runtime/context.py`

```
@classmethod
def get_request_id(cls) -> Optional[str]:
    """Get current request ID."""
    try:
        return cls._request_id.get()
    except LookupError:
        return None
```

#### `get_session_id()`

Get current session ID.

Source code in `bedrock_agentcore/runtime/context.py`

```
@classmethod
def get_session_id(cls) -> Optional[str]:
    """Get current session ID."""
    try:
        return cls._session_id.get()
    except LookupError:
        return None
```

#### `get_workload_access_token()`

Get the workload access token from the context.

Source code in `bedrock_agentcore/runtime/context.py`

```
@classmethod
def get_workload_access_token(cls) -> Optional[str]:
    """Get the workload access token from the context."""
    try:
        return cls._workload_access_token.get()
    except LookupError:
        return None
```

#### `set_oauth2_callback_url(workload_callback_url)`

Set the oauth2 callback url in the context.

Source code in `bedrock_agentcore/runtime/context.py`

```
@classmethod
def set_oauth2_callback_url(cls, workload_callback_url: str):
    """Set the oauth2 callback url in the context."""
    cls._oauth2_callback_url.set(workload_callback_url)
```

#### `set_request_context(request_id, session_id=None)`

Set request-scoped identifiers.

Source code in `bedrock_agentcore/runtime/context.py`

```
@classmethod
def set_request_context(cls, request_id: str, session_id: Optional[str] = None):
    """Set request-scoped identifiers."""
    cls._request_id.set(request_id)
    cls._session_id.set(session_id)
```

#### `set_request_headers(headers)`

Set request headers in the context.

Source code in `bedrock_agentcore/runtime/context.py`

```
@classmethod
def set_request_headers(cls, headers: Dict[str, str]):
    """Set request headers in the context."""
    cls._request_headers.set(headers)
```

#### `set_workload_access_token(token)`

Set the workload access token in the context.

Source code in `bedrock_agentcore/runtime/context.py`

```
@classmethod
def set_workload_access_token(cls, token: str):
    """Set the workload access token in the context."""
    cls._workload_access_token.set(token)
```

### `PingStatus`

Bases: `str`, `Enum`

Ping status enum for health check responses.

Source code in `bedrock_agentcore/runtime/models.py`

```
class PingStatus(str, Enum):
    """Ping status enum for health check responses."""

    HEALTHY = "Healthy"
    HEALTHY_BUSY = "HealthyBusy"
```

### `RequestContext`

Bases: `BaseModel`

Request context containing metadata from HTTP requests.

Source code in `bedrock_agentcore/runtime/context.py`

```
class RequestContext(BaseModel):
    """Request context containing metadata from HTTP requests."""

    session_id: Optional[str] = Field(None)
    request_headers: Optional[Dict[str, str]] = Field(None)
    request: Optional[Any] = Field(None, description="The underlying Starlette request object")

    class Config:
        """Allow non-serializable types like Starlette Request."""

        arbitrary_types_allowed = True
```

#### `Config`

Allow non-serializable types like Starlette Request.

Source code in `bedrock_agentcore/runtime/context.py`

```
class Config:
    """Allow non-serializable types like Starlette Request."""

    arbitrary_types_allowed = True
```
