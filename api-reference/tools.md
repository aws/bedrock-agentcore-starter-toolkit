# Tools

Tools and utilities for Bedrock AgentCore SDK including browser and code interpreter tools.

## `bedrock_agentcore.tools.code_interpreter_client`

Client for interacting with the Code Interpreter sandbox service.

This module provides a client for the AWS Code Interpreter sandbox, allowing applications to start, stop, and invoke code execution in a managed sandbox environment.

### `CodeInterpreter`

Client for interacting with the AWS Code Interpreter sandbox service.

This client handles the session lifecycle and method invocation for Code Interpreter sandboxes, providing an interface to execute code in a secure, managed environment.

Attributes:

| Name                      | Type  | Description                                        |
| ------------------------- | ----- | -------------------------------------------------- |
| `region`                  | `str` | The AWS region being used.                         |
| `control_plane_client`    |       | The boto3 client for control plane operations.     |
| `data_plane_service_name` | `str` | AWS service name for the data plane.               |
| `client`                  | `str` | The boto3 client for interacting with the service. |
| `identifier`              | `str` | The code interpreter identifier.                   |
| `session_id`              | `str` | The active session ID.                             |

Source code in `bedrock_agentcore/tools/code_interpreter_client.py`

```
class CodeInterpreter:
    """Client for interacting with the AWS Code Interpreter sandbox service.

    This client handles the session lifecycle and method invocation for
    Code Interpreter sandboxes, providing an interface to execute code
    in a secure, managed environment.

    Attributes:
        region (str): The AWS region being used.
        control_plane_client: The boto3 client for control plane operations.
        data_plane_service_name (str): AWS service name for the data plane.
        client: The boto3 client for interacting with the service.
        identifier (str, optional): The code interpreter identifier.
        session_id (str, optional): The active session ID.
    """

    def __init__(self, region: str, session: Optional[boto3.Session] = None) -> None:
        """Initialize a Code Interpreter client for the specified AWS region.

        Args:
            region (str): The AWS region to use.
            session (Optional[boto3.Session]): Optional boto3 session.
        """
        self.region = region
        self.logger = logging.getLogger(__name__)

        if session is None:
            session = boto3.Session()

        # Control plane client for interpreter management
        self.control_plane_client = session.client(
            "bedrock-agentcore-control",
            region_name=region,
            endpoint_url=get_control_plane_endpoint(region),
        )

        # Data plane client for session operations
        self.data_plane_client = session.client(
            "bedrock-agentcore",
            region_name=region,
            endpoint_url=get_data_plane_endpoint(region),
        )

        self._identifier = None
        self._session_id = None

    @property
    def identifier(self) -> Optional[str]:
        """Get the current code interpreter identifier."""
        return self._identifier

    @identifier.setter
    def identifier(self, value: Optional[str]):
        """Set the code interpreter identifier."""
        self._identifier = value

    @property
    def session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self._session_id

    @session_id.setter
    def session_id(self, value: Optional[str]):
        """Set the session ID."""
        self._session_id = value

    def create_code_interpreter(
        self,
        name: str,
        execution_role_arn: str,
        network_configuration: Optional[Dict] = None,
        description: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None,
        client_token: Optional[str] = None,
    ) -> Dict:
        """Create a custom code interpreter with specific configuration.

        This is a control plane operation that provisions a new code interpreter
        with custom settings including VPC configuration.

        Args:
            name (str): The name for the code interpreter.
                Must match pattern [a-zA-Z][a-zA-Z0-9_]{0,47}
            execution_role_arn (str): IAM role ARN with permissions for interpreter operations
            network_configuration (Optional[Dict]): Network configuration:
                {
                    "networkMode": "PUBLIC" or "VPC",
                    "vpcConfig": {  # Required if networkMode is VPC
                        "securityGroups": ["sg-xxx"],
                        "subnets": ["subnet-xxx"]
                    }
                }
            description (Optional[str]): Description of the interpreter (1-4096 chars)
            tags (Optional[Dict[str, str]]): Tags for the interpreter
            client_token (Optional[str]): Idempotency token

        Returns:
            Dict: Response containing:
                - codeInterpreterArn (str): ARN of created interpreter
                - codeInterpreterId (str): Unique interpreter identifier
                - createdAt (datetime): Creation timestamp
                - status (str): Interpreter status (CREATING, READY, etc.)

        Example:
            >>> client = CodeInterpreter('us-west-2')
            >>> # Create interpreter with VPC
            >>> response = client.create_code_interpreter(
            ...     name="my_secure_interpreter",
            ...     execution_role_arn="arn:aws:iam::123456789012:role/InterpreterRole",
            ...     network_configuration={
            ...         "networkMode": "VPC",
            ...         "vpcConfig": {
            ...             "securityGroups": ["sg-12345"],
            ...             "subnets": ["subnet-abc123"]
            ...         }
            ...     },
            ...     description="Secure interpreter for data analysis"
            ... )
            >>> interpreter_id = response['codeInterpreterId']
        """
        self.logger.info("Creating code interpreter: %s", name)

        request_params = {
            "name": name,
            "executionRoleArn": execution_role_arn,
            "networkConfiguration": network_configuration or {"networkMode": "PUBLIC"},
        }

        if description:
            request_params["description"] = description

        if tags:
            request_params["tags"] = tags

        if client_token:
            request_params["clientToken"] = client_token

        response = self.control_plane_client.create_code_interpreter(**request_params)
        return response

    def delete_code_interpreter(self, interpreter_id: str, client_token: Optional[str] = None) -> Dict:
        """Delete a custom code interpreter.

        Args:
            interpreter_id (str): The code interpreter identifier to delete
            client_token (Optional[str]): Idempotency token

        Returns:
            Dict: Response containing:
                - codeInterpreterId (str): ID of deleted interpreter
                - lastUpdatedAt (datetime): Update timestamp
                - status (str): Deletion status

        Example:
            >>> client.delete_code_interpreter("my-interpreter-abc123")
        """
        self.logger.info("Deleting code interpreter: %s", interpreter_id)

        request_params = {"codeInterpreterId": interpreter_id}
        if client_token:
            request_params["clientToken"] = client_token

        response = self.control_plane_client.delete_code_interpreter(**request_params)
        return response

    def get_code_interpreter(self, interpreter_id: str) -> Dict:
        """Get detailed information about a code interpreter.

        Args:
            interpreter_id (str): The code interpreter identifier

        Returns:
            Dict: Interpreter details including:
                - codeInterpreterArn, codeInterpreterId, name, description
                - createdAt, lastUpdatedAt
                - executionRoleArn
                - networkConfiguration
                - status (CREATING, CREATE_FAILED, READY, DELETING, etc.)
                - failureReason (if failed)

        Example:
            >>> interpreter_info = client.get_code_interpreter("my-interpreter-abc123")
            >>> print(f"Status: {interpreter_info['status']}")
        """
        self.logger.info("Getting code interpreter: %s", interpreter_id)
        response = self.control_plane_client.get_code_interpreter(codeInterpreterId=interpreter_id)
        return response

    def list_code_interpreters(
        self,
        interpreter_type: Optional[str] = None,
        max_results: int = 10,
        next_token: Optional[str] = None,
    ) -> Dict:
        """List all code interpreters in the account.

        Args:
            interpreter_type (Optional[str]): Filter by type: "SYSTEM" or "CUSTOM"
            max_results (int): Maximum results to return (1-100, default 10)
            next_token (Optional[str]): Token for pagination

        Returns:
            Dict: Response containing:
                - codeInterpreterSummaries (List[Dict]): List of interpreter summaries
                - nextToken (str): Token for next page (if more results)

        Example:
            >>> # List all custom interpreters
            >>> response = client.list_code_interpreters(interpreter_type="CUSTOM")
            >>> for interp in response['codeInterpreterSummaries']:
            ...     print(f"{interp['name']}: {interp['status']}")
        """
        self.logger.info("Listing code interpreters (type=%s)", interpreter_type)

        request_params = {"maxResults": max_results}
        if interpreter_type:
            request_params["type"] = interpreter_type
        if next_token:
            request_params["nextToken"] = next_token

        response = self.control_plane_client.list_code_interpreters(**request_params)
        return response

    def start(
        self,
        identifier: Optional[str] = DEFAULT_IDENTIFIER,
        name: Optional[str] = None,
        session_timeout_seconds: Optional[int] = DEFAULT_TIMEOUT,
    ) -> str:
        """Start a code interpreter sandbox session.

        Args:
            identifier (Optional[str]): The interpreter identifier to use.
                Can be DEFAULT_IDENTIFIER or a custom interpreter ID from create_code_interpreter.
            name (Optional[str]): A name for this session.
            session_timeout_seconds (Optional[int]): The timeout in seconds.
                Default: 900 (15 minutes).

        Returns:
            str: The session ID of the newly created session.

        Example:
            >>> # Use system interpreter
            >>> session_id = client.start()
            >>>
            >>> # Use custom interpreter with VPC
            >>> session_id = client.start(
            ...     identifier="my-interpreter-abc123",
            ...     session_timeout_seconds=1800  # 30 minutes
            ... )
        """
        self.logger.info("Starting code interpreter session...")

        response = self.data_plane_client.start_code_interpreter_session(
            codeInterpreterIdentifier=identifier,
            name=name or f"code-session-{uuid.uuid4().hex[:8]}",
            sessionTimeoutSeconds=session_timeout_seconds,
        )

        self.identifier = response["codeInterpreterIdentifier"]
        self.session_id = response["sessionId"]

        self.logger.info("✅ Session started: %s", self.session_id)
        return self.session_id

    def stop(self) -> bool:
        """Stop the current code interpreter session if one is active.

        Returns:
            bool: True if successful or no session was active.
        """
        self.logger.info("Stopping code interpreter session...")

        if not self.session_id or not self.identifier:
            return True

        self.data_plane_client.stop_code_interpreter_session(
            codeInterpreterIdentifier=self.identifier, sessionId=self.session_id
        )

        self.logger.info("✅ Session stopped: %s", self.session_id)
        self.identifier = None
        self.session_id = None
        return True

    def get_session(self, interpreter_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict:
        """Get detailed information about a code interpreter session.

        Args:
            interpreter_id (Optional[str]): Interpreter ID (uses current if not provided)
            session_id (Optional[str]): Session ID (uses current if not provided)

        Returns:
            Dict: Session details including:
                - sessionId, codeInterpreterIdentifier, name
                - status (READY, TERMINATED)
                - createdAt, lastUpdatedAt
                - sessionTimeoutSeconds

        Example:
            >>> session_info = client.get_session()
            >>> print(f"Session status: {session_info['status']}")
        """
        interpreter_id = interpreter_id or self.identifier
        session_id = session_id or self.session_id

        if not interpreter_id or not session_id:
            raise ValueError("Interpreter ID and Session ID must be provided or available from current session")

        self.logger.info("Getting session: %s", session_id)

        response = self.data_plane_client.get_code_interpreter_session(
            codeInterpreterIdentifier=interpreter_id, sessionId=session_id
        )
        return response

    def list_sessions(
        self,
        interpreter_id: Optional[str] = None,
        status: Optional[str] = None,
        max_results: int = 10,
        next_token: Optional[str] = None,
    ) -> Dict:
        """List code interpreter sessions for a specific interpreter.

        Args:
            interpreter_id (Optional[str]): Interpreter ID (uses current if not provided)
            status (Optional[str]): Filter by status: "READY" or "TERMINATED"
            max_results (int): Maximum results (1-100, default 10)
            next_token (Optional[str]): Pagination token

        Returns:
            Dict: Response containing:
                - items (List[Dict]): List of session summaries
                - nextToken (str): Token for next page (if more results)

        Example:
            >>> # List all active sessions
            >>> response = client.list_sessions(status="READY")
            >>> for session in response['items']:
            ...     print(f"Session {session['sessionId']}: {session['status']}")
        """
        interpreter_id = interpreter_id or self.identifier
        if not interpreter_id:
            raise ValueError("Interpreter ID must be provided or available from current session")

        self.logger.info("Listing sessions for interpreter: %s", interpreter_id)

        request_params = {"codeInterpreterIdentifier": interpreter_id, "maxResults": max_results}
        if status:
            request_params["status"] = status
        if next_token:
            request_params["nextToken"] = next_token

        response = self.data_plane_client.list_code_interpreter_sessions(**request_params)
        return response

    def invoke(self, method: str, params: Optional[Dict] = None):
        r"""Invoke a method in the code interpreter sandbox.

        If no session is active, automatically starts a new session.

        Args:
            method (str): The name of the method to invoke.
            params (Optional[Dict]): Parameters to pass to the method.

        Returns:
            dict: The response from the code interpreter service.

        Example:
            >>> # List files in the sandbox
            >>> result = client.invoke('listFiles')
            >>>
            >>> # Execute Python code
            >>> code = "import pandas as pd\\ndf = pd.DataFrame({'a': [1,2,3]})\\nprint(df)"
            >>> result = client.invoke('execute', {'code': code})
        """
        if not self.session_id or not self.identifier:
            self.start()

        return self.data_plane_client.invoke_code_interpreter(
            codeInterpreterIdentifier=self.identifier,
            sessionId=self.session_id,
            name=method,
            arguments=params or {},
        )
```

#### `identifier`

Get the current code interpreter identifier.

#### `session_id`

Get the current session ID.

#### `__init__(region, session=None)`

Initialize a Code Interpreter client for the specified AWS region.

Parameters:

| Name      | Type                | Description             | Default    |
| --------- | ------------------- | ----------------------- | ---------- |
| `region`  | `str`               | The AWS region to use.  | *required* |
| `session` | `Optional[Session]` | Optional boto3 session. | `None`     |

Source code in `bedrock_agentcore/tools/code_interpreter_client.py`

```
def __init__(self, region: str, session: Optional[boto3.Session] = None) -> None:
    """Initialize a Code Interpreter client for the specified AWS region.

    Args:
        region (str): The AWS region to use.
        session (Optional[boto3.Session]): Optional boto3 session.
    """
    self.region = region
    self.logger = logging.getLogger(__name__)

    if session is None:
        session = boto3.Session()

    # Control plane client for interpreter management
    self.control_plane_client = session.client(
        "bedrock-agentcore-control",
        region_name=region,
        endpoint_url=get_control_plane_endpoint(region),
    )

    # Data plane client for session operations
    self.data_plane_client = session.client(
        "bedrock-agentcore",
        region_name=region,
        endpoint_url=get_data_plane_endpoint(region),
    )

    self._identifier = None
    self._session_id = None
```

#### `create_code_interpreter(name, execution_role_arn, network_configuration=None, description=None, tags=None, client_token=None)`

Create a custom code interpreter with specific configuration.

This is a control plane operation that provisions a new code interpreter with custom settings including VPC configuration.

Parameters:

| Name                    | Type                       | Description                                                                                                                                                            | Default    |
| ----------------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `name`                  | `str`                      | The name for the code interpreter. Must match pattern a-zA-Z                                                                                                           | *required* |
| `execution_role_arn`    | `str`                      | IAM role ARN with permissions for interpreter operations                                                                                                               | *required* |
| `network_configuration` | `Optional[Dict]`           | Network configuration: { "networkMode": "PUBLIC" or "VPC", "vpcConfig": { # Required if networkMode is VPC "securityGroups": ["sg-xxx"], "subnets": ["subnet-xxx"] } } | `None`     |
| `description`           | `Optional[str]`            | Description of the interpreter (1-4096 chars)                                                                                                                          | `None`     |
| `tags`                  | `Optional[Dict[str, str]]` | Tags for the interpreter                                                                                                                                               | `None`     |
| `client_token`          | `Optional[str]`            | Idempotency token                                                                                                                                                      | `None`     |

Returns:

| Name   | Type   | Description                                                                                                                                                                                                                                |
| ------ | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Dict` | `Dict` | Response containing: - codeInterpreterArn (str): ARN of created interpreter - codeInterpreterId (str): Unique interpreter identifier - createdAt (datetime): Creation timestamp - status (str): Interpreter status (CREATING, READY, etc.) |

Example

> > > client = CodeInterpreter('us-west-2')
> > >
> > > ##### Create interpreter with VPC
> > >
> > > response = client.create_code_interpreter( ... name="my_secure_interpreter", ... execution_role_arn="arn:aws:iam::123456789012:role/InterpreterRole", ... network_configuration={ ... "networkMode": "VPC", ... "vpcConfig": { ... "securityGroups": ["sg-12345"], ... "subnets": ["subnet-abc123"] ... } ... }, ... description="Secure interpreter for data analysis" ... ) interpreter_id = response['codeInterpreterId']

Source code in `bedrock_agentcore/tools/code_interpreter_client.py`

```
def create_code_interpreter(
    self,
    name: str,
    execution_role_arn: str,
    network_configuration: Optional[Dict] = None,
    description: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    client_token: Optional[str] = None,
) -> Dict:
    """Create a custom code interpreter with specific configuration.

    This is a control plane operation that provisions a new code interpreter
    with custom settings including VPC configuration.

    Args:
        name (str): The name for the code interpreter.
            Must match pattern [a-zA-Z][a-zA-Z0-9_]{0,47}
        execution_role_arn (str): IAM role ARN with permissions for interpreter operations
        network_configuration (Optional[Dict]): Network configuration:
            {
                "networkMode": "PUBLIC" or "VPC",
                "vpcConfig": {  # Required if networkMode is VPC
                    "securityGroups": ["sg-xxx"],
                    "subnets": ["subnet-xxx"]
                }
            }
        description (Optional[str]): Description of the interpreter (1-4096 chars)
        tags (Optional[Dict[str, str]]): Tags for the interpreter
        client_token (Optional[str]): Idempotency token

    Returns:
        Dict: Response containing:
            - codeInterpreterArn (str): ARN of created interpreter
            - codeInterpreterId (str): Unique interpreter identifier
            - createdAt (datetime): Creation timestamp
            - status (str): Interpreter status (CREATING, READY, etc.)

    Example:
        >>> client = CodeInterpreter('us-west-2')
        >>> # Create interpreter with VPC
        >>> response = client.create_code_interpreter(
        ...     name="my_secure_interpreter",
        ...     execution_role_arn="arn:aws:iam::123456789012:role/InterpreterRole",
        ...     network_configuration={
        ...         "networkMode": "VPC",
        ...         "vpcConfig": {
        ...             "securityGroups": ["sg-12345"],
        ...             "subnets": ["subnet-abc123"]
        ...         }
        ...     },
        ...     description="Secure interpreter for data analysis"
        ... )
        >>> interpreter_id = response['codeInterpreterId']
    """
    self.logger.info("Creating code interpreter: %s", name)

    request_params = {
        "name": name,
        "executionRoleArn": execution_role_arn,
        "networkConfiguration": network_configuration or {"networkMode": "PUBLIC"},
    }

    if description:
        request_params["description"] = description

    if tags:
        request_params["tags"] = tags

    if client_token:
        request_params["clientToken"] = client_token

    response = self.control_plane_client.create_code_interpreter(**request_params)
    return response
```

#### `delete_code_interpreter(interpreter_id, client_token=None)`

Delete a custom code interpreter.

Parameters:

| Name             | Type            | Description                               | Default    |
| ---------------- | --------------- | ----------------------------------------- | ---------- |
| `interpreter_id` | `str`           | The code interpreter identifier to delete | *required* |
| `client_token`   | `Optional[str]` | Idempotency token                         | `None`     |

Returns:

| Name   | Type   | Description                                                                                                                                            |
| ------ | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Dict` | `Dict` | Response containing: - codeInterpreterId (str): ID of deleted interpreter - lastUpdatedAt (datetime): Update timestamp - status (str): Deletion status |

Example

> > > client.delete_code_interpreter("my-interpreter-abc123")

Source code in `bedrock_agentcore/tools/code_interpreter_client.py`

```
def delete_code_interpreter(self, interpreter_id: str, client_token: Optional[str] = None) -> Dict:
    """Delete a custom code interpreter.

    Args:
        interpreter_id (str): The code interpreter identifier to delete
        client_token (Optional[str]): Idempotency token

    Returns:
        Dict: Response containing:
            - codeInterpreterId (str): ID of deleted interpreter
            - lastUpdatedAt (datetime): Update timestamp
            - status (str): Deletion status

    Example:
        >>> client.delete_code_interpreter("my-interpreter-abc123")
    """
    self.logger.info("Deleting code interpreter: %s", interpreter_id)

    request_params = {"codeInterpreterId": interpreter_id}
    if client_token:
        request_params["clientToken"] = client_token

    response = self.control_plane_client.delete_code_interpreter(**request_params)
    return response
```

#### `get_code_interpreter(interpreter_id)`

Get detailed information about a code interpreter.

Parameters:

| Name             | Type  | Description                     | Default    |
| ---------------- | ----- | ------------------------------- | ---------- |
| `interpreter_id` | `str` | The code interpreter identifier | *required* |

Returns:

| Name   | Type   | Description                                                                                                                                                                                                                                          |
| ------ | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Dict` | `Dict` | Interpreter details including: - codeInterpreterArn, codeInterpreterId, name, description - createdAt, lastUpdatedAt - executionRoleArn - networkConfiguration - status (CREATING, CREATE_FAILED, READY, DELETING, etc.) - failureReason (if failed) |

Example

> > > interpreter_info = client.get_code_interpreter("my-interpreter-abc123") print(f"Status: {interpreter_info['status']}")

Source code in `bedrock_agentcore/tools/code_interpreter_client.py`

```
def get_code_interpreter(self, interpreter_id: str) -> Dict:
    """Get detailed information about a code interpreter.

    Args:
        interpreter_id (str): The code interpreter identifier

    Returns:
        Dict: Interpreter details including:
            - codeInterpreterArn, codeInterpreterId, name, description
            - createdAt, lastUpdatedAt
            - executionRoleArn
            - networkConfiguration
            - status (CREATING, CREATE_FAILED, READY, DELETING, etc.)
            - failureReason (if failed)

    Example:
        >>> interpreter_info = client.get_code_interpreter("my-interpreter-abc123")
        >>> print(f"Status: {interpreter_info['status']}")
    """
    self.logger.info("Getting code interpreter: %s", interpreter_id)
    response = self.control_plane_client.get_code_interpreter(codeInterpreterId=interpreter_id)
    return response
```

#### `get_session(interpreter_id=None, session_id=None)`

Get detailed information about a code interpreter session.

Parameters:

| Name             | Type            | Description                                   | Default |
| ---------------- | --------------- | --------------------------------------------- | ------- |
| `interpreter_id` | `Optional[str]` | Interpreter ID (uses current if not provided) | `None`  |
| `session_id`     | `Optional[str]` | Session ID (uses current if not provided)     | `None`  |

Returns:

| Name   | Type   | Description                                                                                                                                             |
| ------ | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Dict` | `Dict` | Session details including: - sessionId, codeInterpreterIdentifier, name - status (READY, TERMINATED) - createdAt, lastUpdatedAt - sessionTimeoutSeconds |

Example

> > > session_info = client.get_session() print(f"Session status: {session_info['status']}")

Source code in `bedrock_agentcore/tools/code_interpreter_client.py`

```
def get_session(self, interpreter_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict:
    """Get detailed information about a code interpreter session.

    Args:
        interpreter_id (Optional[str]): Interpreter ID (uses current if not provided)
        session_id (Optional[str]): Session ID (uses current if not provided)

    Returns:
        Dict: Session details including:
            - sessionId, codeInterpreterIdentifier, name
            - status (READY, TERMINATED)
            - createdAt, lastUpdatedAt
            - sessionTimeoutSeconds

    Example:
        >>> session_info = client.get_session()
        >>> print(f"Session status: {session_info['status']}")
    """
    interpreter_id = interpreter_id or self.identifier
    session_id = session_id or self.session_id

    if not interpreter_id or not session_id:
        raise ValueError("Interpreter ID and Session ID must be provided or available from current session")

    self.logger.info("Getting session: %s", session_id)

    response = self.data_plane_client.get_code_interpreter_session(
        codeInterpreterIdentifier=interpreter_id, sessionId=session_id
    )
    return response
```

#### `invoke(method, params=None)`

Invoke a method in the code interpreter sandbox.

If no session is active, automatically starts a new session.

Parameters:

| Name     | Type             | Description                       | Default    |
| -------- | ---------------- | --------------------------------- | ---------- |
| `method` | `str`            | The name of the method to invoke. | *required* |
| `params` | `Optional[Dict]` | Parameters to pass to the method. | `None`     |

Returns:

| Name   | Type | Description                                     |
| ------ | ---- | ----------------------------------------------- |
| `dict` |      | The response from the code interpreter service. |

Example

> > > ##### List files in the sandbox
> > >
> > > result = client.invoke('listFiles')
> > >
> > > ##### Execute Python code
> > >
> > > code = "import pandas as pd\\ndf = pd.DataFrame({'a': [1,2,3]})\\nprint(df)" result = client.invoke('execute', {'code': code})

Source code in `bedrock_agentcore/tools/code_interpreter_client.py`

```
def invoke(self, method: str, params: Optional[Dict] = None):
    r"""Invoke a method in the code interpreter sandbox.

    If no session is active, automatically starts a new session.

    Args:
        method (str): The name of the method to invoke.
        params (Optional[Dict]): Parameters to pass to the method.

    Returns:
        dict: The response from the code interpreter service.

    Example:
        >>> # List files in the sandbox
        >>> result = client.invoke('listFiles')
        >>>
        >>> # Execute Python code
        >>> code = "import pandas as pd\\ndf = pd.DataFrame({'a': [1,2,3]})\\nprint(df)"
        >>> result = client.invoke('execute', {'code': code})
    """
    if not self.session_id or not self.identifier:
        self.start()

    return self.data_plane_client.invoke_code_interpreter(
        codeInterpreterIdentifier=self.identifier,
        sessionId=self.session_id,
        name=method,
        arguments=params or {},
    )
```

#### `list_code_interpreters(interpreter_type=None, max_results=10, next_token=None)`

List all code interpreters in the account.

Parameters:

| Name               | Type            | Description                                   | Default |
| ------------------ | --------------- | --------------------------------------------- | ------- |
| `interpreter_type` | `Optional[str]` | Filter by type: "SYSTEM" or "CUSTOM"          | `None`  |
| `max_results`      | `int`           | Maximum results to return (1-100, default 10) | `10`    |
| `next_token`       | `Optional[str]` | Token for pagination                          | `None`  |

Returns:

| Name   | Type   | Description                                                                                                                                          |
| ------ | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Dict` | `Dict` | Response containing: - codeInterpreterSummaries (List[Dict]): List of interpreter summaries - nextToken (str): Token for next page (if more results) |

Example

> > > ##### List all custom interpreters
> > >
> > > response = client.list_code_interpreters(interpreter_type="CUSTOM") for interp in response\['codeInterpreterSummaries'\]: ... print(f"{interp['name']}: {interp['status']}")

Source code in `bedrock_agentcore/tools/code_interpreter_client.py`

```
def list_code_interpreters(
    self,
    interpreter_type: Optional[str] = None,
    max_results: int = 10,
    next_token: Optional[str] = None,
) -> Dict:
    """List all code interpreters in the account.

    Args:
        interpreter_type (Optional[str]): Filter by type: "SYSTEM" or "CUSTOM"
        max_results (int): Maximum results to return (1-100, default 10)
        next_token (Optional[str]): Token for pagination

    Returns:
        Dict: Response containing:
            - codeInterpreterSummaries (List[Dict]): List of interpreter summaries
            - nextToken (str): Token for next page (if more results)

    Example:
        >>> # List all custom interpreters
        >>> response = client.list_code_interpreters(interpreter_type="CUSTOM")
        >>> for interp in response['codeInterpreterSummaries']:
        ...     print(f"{interp['name']}: {interp['status']}")
    """
    self.logger.info("Listing code interpreters (type=%s)", interpreter_type)

    request_params = {"maxResults": max_results}
    if interpreter_type:
        request_params["type"] = interpreter_type
    if next_token:
        request_params["nextToken"] = next_token

    response = self.control_plane_client.list_code_interpreters(**request_params)
    return response
```

#### `list_sessions(interpreter_id=None, status=None, max_results=10, next_token=None)`

List code interpreter sessions for a specific interpreter.

Parameters:

| Name             | Type            | Description                                   | Default |
| ---------------- | --------------- | --------------------------------------------- | ------- |
| `interpreter_id` | `Optional[str]` | Interpreter ID (uses current if not provided) | `None`  |
| `status`         | `Optional[str]` | Filter by status: "READY" or "TERMINATED"     | `None`  |
| `max_results`    | `int`           | Maximum results (1-100, default 10)           | `10`    |
| `next_token`     | `Optional[str]` | Pagination token                              | `None`  |

Returns:

| Name   | Type   | Description                                                                                                                   |
| ------ | ------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `Dict` | `Dict` | Response containing: - items (List[Dict]): List of session summaries - nextToken (str): Token for next page (if more results) |

Example

> > > ##### List all active sessions
> > >
> > > response = client.list_sessions(status="READY") for session in response\['items'\]: ... print(f"Session {session['sessionId']}: {session['status']}")

Source code in `bedrock_agentcore/tools/code_interpreter_client.py`

```
def list_sessions(
    self,
    interpreter_id: Optional[str] = None,
    status: Optional[str] = None,
    max_results: int = 10,
    next_token: Optional[str] = None,
) -> Dict:
    """List code interpreter sessions for a specific interpreter.

    Args:
        interpreter_id (Optional[str]): Interpreter ID (uses current if not provided)
        status (Optional[str]): Filter by status: "READY" or "TERMINATED"
        max_results (int): Maximum results (1-100, default 10)
        next_token (Optional[str]): Pagination token

    Returns:
        Dict: Response containing:
            - items (List[Dict]): List of session summaries
            - nextToken (str): Token for next page (if more results)

    Example:
        >>> # List all active sessions
        >>> response = client.list_sessions(status="READY")
        >>> for session in response['items']:
        ...     print(f"Session {session['sessionId']}: {session['status']}")
    """
    interpreter_id = interpreter_id or self.identifier
    if not interpreter_id:
        raise ValueError("Interpreter ID must be provided or available from current session")

    self.logger.info("Listing sessions for interpreter: %s", interpreter_id)

    request_params = {"codeInterpreterIdentifier": interpreter_id, "maxResults": max_results}
    if status:
        request_params["status"] = status
    if next_token:
        request_params["nextToken"] = next_token

    response = self.data_plane_client.list_code_interpreter_sessions(**request_params)
    return response
```

#### `start(identifier=DEFAULT_IDENTIFIER, name=None, session_timeout_seconds=DEFAULT_TIMEOUT)`

Start a code interpreter sandbox session.

Parameters:

| Name                      | Type            | Description                                                                                                           | Default              |
| ------------------------- | --------------- | --------------------------------------------------------------------------------------------------------------------- | -------------------- |
| `identifier`              | `Optional[str]` | The interpreter identifier to use. Can be DEFAULT_IDENTIFIER or a custom interpreter ID from create_code_interpreter. | `DEFAULT_IDENTIFIER` |
| `name`                    | `Optional[str]` | A name for this session.                                                                                              | `None`               |
| `session_timeout_seconds` | `Optional[int]` | The timeout in seconds. Default: 900 (15 minutes).                                                                    | `DEFAULT_TIMEOUT`    |

Returns:

| Name  | Type  | Description                                  |
| ----- | ----- | -------------------------------------------- |
| `str` | `str` | The session ID of the newly created session. |

Example

> > > ##### Use system interpreter
> > >
> > > session_id = client.start()
> > >
> > > ##### Use custom interpreter with VPC
> > >
> > > session_id = client.start( ... identifier="my-interpreter-abc123", ... session_timeout_seconds=1800 # 30 minutes ... )

Source code in `bedrock_agentcore/tools/code_interpreter_client.py`

```
def start(
    self,
    identifier: Optional[str] = DEFAULT_IDENTIFIER,
    name: Optional[str] = None,
    session_timeout_seconds: Optional[int] = DEFAULT_TIMEOUT,
) -> str:
    """Start a code interpreter sandbox session.

    Args:
        identifier (Optional[str]): The interpreter identifier to use.
            Can be DEFAULT_IDENTIFIER or a custom interpreter ID from create_code_interpreter.
        name (Optional[str]): A name for this session.
        session_timeout_seconds (Optional[int]): The timeout in seconds.
            Default: 900 (15 minutes).

    Returns:
        str: The session ID of the newly created session.

    Example:
        >>> # Use system interpreter
        >>> session_id = client.start()
        >>>
        >>> # Use custom interpreter with VPC
        >>> session_id = client.start(
        ...     identifier="my-interpreter-abc123",
        ...     session_timeout_seconds=1800  # 30 minutes
        ... )
    """
    self.logger.info("Starting code interpreter session...")

    response = self.data_plane_client.start_code_interpreter_session(
        codeInterpreterIdentifier=identifier,
        name=name or f"code-session-{uuid.uuid4().hex[:8]}",
        sessionTimeoutSeconds=session_timeout_seconds,
    )

    self.identifier = response["codeInterpreterIdentifier"]
    self.session_id = response["sessionId"]

    self.logger.info("✅ Session started: %s", self.session_id)
    return self.session_id
```

#### `stop()`

Stop the current code interpreter session if one is active.

Returns:

| Name   | Type   | Description                                  |
| ------ | ------ | -------------------------------------------- |
| `bool` | `bool` | True if successful or no session was active. |

Source code in `bedrock_agentcore/tools/code_interpreter_client.py`

```
def stop(self) -> bool:
    """Stop the current code interpreter session if one is active.

    Returns:
        bool: True if successful or no session was active.
    """
    self.logger.info("Stopping code interpreter session...")

    if not self.session_id or not self.identifier:
        return True

    self.data_plane_client.stop_code_interpreter_session(
        codeInterpreterIdentifier=self.identifier, sessionId=self.session_id
    )

    self.logger.info("✅ Session stopped: %s", self.session_id)
    self.identifier = None
    self.session_id = None
    return True
```

### `code_session(region, session=None, identifier=None)`

Context manager for creating and managing a code interpreter session.

Parameters:

| Name         | Type                | Description                                | Default    |
| ------------ | ------------------- | ------------------------------------------ | ---------- |
| `region`     | `str`               | AWS region.                                | *required* |
| `session`    | `Optional[Session]` | Optional boto3 session.                    | `None`     |
| `identifier` | `Optional[str]`     | Interpreter identifier (system or custom). | `None`     |

Yields:

| Name              | Type              | Description                                         |
| ----------------- | ----------------- | --------------------------------------------------- |
| `CodeInterpreter` | `CodeInterpreter` | An initialized and started code interpreter client. |

Example

> > > #### Use system interpreter
> > >
> > > with code_session('us-west-2') as client: ... result = client.invoke('listFiles') ...
> > >
> > > #### Use custom VPC interpreter
> > >
> > > with code_session('us-west-2', identifier='my-secure-interpreter') as client: ... # Secure data analysis ... pass

Source code in `bedrock_agentcore/tools/code_interpreter_client.py`

```
@contextmanager
def code_session(
    region: str, session: Optional[boto3.Session] = None, identifier: Optional[str] = None
) -> Generator[CodeInterpreter, None, None]:
    """Context manager for creating and managing a code interpreter session.

    Args:
        region (str): AWS region.
        session (Optional[boto3.Session]): Optional boto3 session.
        identifier (Optional[str]): Interpreter identifier (system or custom).

    Yields:
        CodeInterpreter: An initialized and started code interpreter client.

    Example:
        >>> # Use system interpreter
        >>> with code_session('us-west-2') as client:
        ...     result = client.invoke('listFiles')
        ...
        >>> # Use custom VPC interpreter
        >>> with code_session('us-west-2', identifier='my-secure-interpreter') as client:
        ...     # Secure data analysis
        ...     pass
    """
    client = CodeInterpreter(region, session=session)
    if identifier is not None:
        client.start(identifier=identifier)
    else:
        client.start()

    try:
        yield client
    finally:
        client.stop()
```

## `bedrock_agentcore.tools.browser_client`

Client for interacting with the Browser sandbox service.

This module provides a client for the AWS Browser sandbox, allowing applications to start, stop, and automate browser interactions in a managed sandbox environment using Playwright.

### `BrowserClient`

Client for interacting with the AWS Browser sandbox service.

This client handles the session lifecycle and browser automation for Browser sandboxes, providing an interface to perform web automation tasks in a secure, managed environment.

Attributes:

| Name                      | Type  | Description                                        |
| ------------------------- | ----- | -------------------------------------------------- |
| `region`                  | `str` | The AWS region being used.                         |
| `control_plane_client`    |       | The boto3 client for control plane operations.     |
| `data_plane_service_name` | `str` | AWS service name for the data plane.               |
| `client`                  | `str` | The boto3 client for interacting with the service. |
| `identifier`              | `str` | The browser identifier.                            |
| `session_id`              | `str` | The active session ID.                             |

Source code in `bedrock_agentcore/tools/browser_client.py`

```
class BrowserClient:
    """Client for interacting with the AWS Browser sandbox service.

    This client handles the session lifecycle and browser automation for
    Browser sandboxes, providing an interface to perform web automation
    tasks in a secure, managed environment.

    Attributes:
        region (str): The AWS region being used.
        control_plane_client: The boto3 client for control plane operations.
        data_plane_service_name (str): AWS service name for the data plane.
        client: The boto3 client for interacting with the service.
        identifier (str, optional): The browser identifier.
        session_id (str, optional): The active session ID.
    """

    def __init__(self, region: str) -> None:
        """Initialize a Browser client for the specified AWS region.

        Args:
            region (str): The AWS region to use for the Browser service.
        """
        self.region = region
        self.logger = logging.getLogger(__name__)

        # Control plane client for browser management
        self.control_plane_client = boto3.client(
            "bedrock-agentcore-control",
            region_name=region,
            endpoint_url=get_control_plane_endpoint(region),
        )

        # Data plane client for session operations
        self.data_plane_client = boto3.client(
            "bedrock-agentcore",
            region_name=region,
            endpoint_url=get_data_plane_endpoint(region),
        )

        self._identifier = None
        self._session_id = None

    @property
    def identifier(self) -> Optional[str]:
        """Get the current browser identifier."""
        return self._identifier

    @identifier.setter
    def identifier(self, value: Optional[str]):
        """Set the browser identifier."""
        self._identifier = value

    @property
    def session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self._session_id

    @session_id.setter
    def session_id(self, value: Optional[str]):
        """Set the session ID."""
        self._session_id = value

    def create_browser(
        self,
        name: str,
        execution_role_arn: str,
        network_configuration: Optional[Dict] = None,
        description: Optional[str] = None,
        recording: Optional[Dict] = None,
        browser_signing: Optional[Dict] = None,
        tags: Optional[Dict[str, str]] = None,
        client_token: Optional[str] = None,
    ) -> Dict:
        """Create a custom browser with specific configuration.

        This is a control plane operation that provisions a new browser with
        custom settings including Web Bot Auth, VPC, and recording configuration.

        Args:
            name (str): The name for the browser. Must match pattern [a-zA-Z][a-zA-Z0-9_]{0,47}
            execution_role_arn (str): IAM role ARN with permissions for browser operations
            network_configuration (Optional[Dict]): Network configuration:
                {
                    "networkMode": "PUBLIC" or "VPC",
                    "vpcConfig": {  # Required if networkMode is VPC
                        "securityGroups": ["sg-xxx"],
                        "subnets": ["subnet-xxx"]
                    }
                }
            description (Optional[str]): Description of the browser (1-4096 chars)
            recording (Optional[Dict]): Recording configuration:
                {
                    "enabled": True,
                    "s3Location": {
                        "bucket": "bucket-name",
                        "keyPrefix": "path/prefix"
                    }
                }
            browser_signing (Optional[Dict]): Web Bot Auth configuration (NEW FEATURE):
                {
                    "enabled": True
                }
            tags (Optional[Dict[str, str]]): Tags for the browser
            client_token (Optional[str]): Idempotency token

        Returns:
            Dict: Response containing:
                - browserArn (str): ARN of created browser
                - browserId (str): Unique browser identifier
                - createdAt (datetime): Creation timestamp
                - status (str): Browser status (CREATING, READY, etc.)

        Example:
            >>> client = BrowserClient('us-west-2')
            >>> # Create browser with Web Bot Auth enabled
            >>> response = client.create_browser(
            ...     name="my_signed_browser",
            ...     execution_role_arn="arn:aws:iam::123456789012:role/BrowserRole",
            ...     network_configuration={"networkMode": "PUBLIC"},
            ...     browser_signing={"enabled": True},
            ...     recording={
            ...         "enabled": True,
            ...         "s3Location": {
            ...             "bucket": "my-recordings",
            ...             "keyPrefix": "browser-sessions/"
            ...         }
            ...     }
            ... )
            >>> browser_id = response['browserId']
        """
        self.logger.info("Creating browser: %s", name)

        request_params = {
            "name": name,
            "executionRoleArn": execution_role_arn,
            "networkConfiguration": network_configuration or {"networkMode": "PUBLIC"},
        }

        if description:
            request_params["description"] = description

        if recording:
            request_params["recording"] = recording

        if browser_signing:
            request_params["browserSigning"] = browser_signing
            self.logger.info("🔐 Web Bot Auth (browserSigning) enabled")

        if tags:
            request_params["tags"] = tags

        if client_token:
            request_params["clientToken"] = client_token

        response = self.control_plane_client.create_browser(**request_params)
        return response

    def delete_browser(self, browser_id: str, client_token: Optional[str] = None) -> Dict:
        """Delete a custom browser.

        Args:
            browser_id (str): The browser identifier to delete
            client_token (Optional[str]): Idempotency token

        Returns:
            Dict: Response containing:
                - browserId (str): ID of deleted browser
                - lastUpdatedAt (datetime): Update timestamp
                - status (str): Deletion status

        Example:
            >>> client.delete_browser("my-browser-abc123")
        """
        self.logger.info("Deleting browser: %s", browser_id)

        request_params = {"browserId": browser_id}
        if client_token:
            request_params["clientToken"] = client_token

        response = self.control_plane_client.delete_browser(**request_params)
        return response

    def get_browser(self, browser_id: str) -> Dict:
        """Get detailed information about a browser.

        Args:
            browser_id (str): The browser identifier

        Returns:
            Dict: Browser details including:
                - browserArn, browserId, name, description
                - createdAt, lastUpdatedAt
                - executionRoleArn
                - networkConfiguration
                - recording configuration
                - browserSigning configuration (if enabled)
                - status (CREATING, CREATE_FAILED, READY, DELETING, etc.)
                - failureReason (if failed)

        Example:
            >>> browser_info = client.get_browser("my-browser-abc123")
            >>> print(f"Status: {browser_info['status']}")
            >>> if browser_info.get('browserSigning'):
            ...     print("Web Bot Auth is enabled!")
        """
        self.logger.info("Getting browser: %s", browser_id)
        response = self.control_plane_client.get_browser(browserId=browser_id)
        return response

    def list_browsers(
        self,
        browser_type: Optional[str] = None,
        max_results: int = 10,
        next_token: Optional[str] = None,
    ) -> Dict:
        """List all browsers in the account.

        Args:
            browser_type (Optional[str]): Filter by type: "SYSTEM" or "CUSTOM"
            max_results (int): Maximum results to return (1-100, default 10)
            next_token (Optional[str]): Token for pagination

        Returns:
            Dict: Response containing:
                - browserSummaries (List[Dict]): List of browser summaries
                - nextToken (str): Token for next page (if more results)

        Example:
            >>> # List all custom browsers
            >>> response = client.list_browsers(browser_type="CUSTOM")
            >>> for browser in response['browserSummaries']:
            ...     print(f"{browser['name']}: {browser['status']}")
        """
        self.logger.info("Listing browsers (type=%s)", browser_type)

        request_params = {"maxResults": max_results}
        if browser_type:
            request_params["type"] = browser_type
        if next_token:
            request_params["nextToken"] = next_token

        response = self.control_plane_client.list_browsers(**request_params)
        return response

    def start(
        self,
        identifier: Optional[str] = DEFAULT_IDENTIFIER,
        name: Optional[str] = None,
        session_timeout_seconds: Optional[int] = DEFAULT_SESSION_TIMEOUT,
        viewport: Optional[Dict[str, int]] = None,
    ) -> str:
        """Start a browser sandbox session.

        This method initializes a new browser session with the provided parameters.

        Args:
            identifier (Optional[str]): The browser sandbox identifier to use.
                Can be DEFAULT_IDENTIFIER or a custom browser ID from create_browser.
            name (Optional[str]): A name for this session.
            session_timeout_seconds (Optional[int]): The timeout for the session in seconds.
                Range: 1-28800 (8 hours). Default: 3600 (1 hour).
            viewport (Optional[Dict[str, int]]): The viewport dimensions:
                {'width': 1920, 'height': 1080}

        Returns:
            str: The session ID of the newly created session.

        Example:
            >>> # Use system browser
            >>> session_id = client.start()
            >>>
            >>> # Use custom browser with Web Bot Auth
            >>> session_id = client.start(
            ...     identifier="my-browser-abc123",
            ...     viewport={'width': 1920, 'height': 1080},
            ...     session_timeout_seconds=7200  # 2 hours
            ... )
        """
        self.logger.info("Starting browser session...")

        request_params = {
            "browserIdentifier": identifier,
            "name": name or f"browser-session-{uuid.uuid4().hex[:8]}",
            "sessionTimeoutSeconds": session_timeout_seconds,
        }

        if viewport is not None:
            request_params["viewPort"] = viewport

        response = self.data_plane_client.start_browser_session(**request_params)

        self.identifier = response["browserIdentifier"]
        self.session_id = response["sessionId"]

        self.logger.info("✅ Session started: %s", self.session_id)
        return self.session_id

    def stop(self) -> bool:
        """Stop the current browser session if one is active.

        Returns:
            bool: True if successful or no session was active.
        """
        self.logger.info("Stopping browser session...")

        if not self.session_id or not self.identifier:
            return True

        self.data_plane_client.stop_browser_session(browserIdentifier=self.identifier, sessionId=self.session_id)

        self.logger.info("✅ Session stopped: %s", self.session_id)
        self.identifier = None
        self.session_id = None
        return True

    def get_session(self, browser_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict:
        """Get detailed information about a browser session.

        Args:
            browser_id (Optional[str]): Browser identifier (uses current if not provided)
            session_id (Optional[str]): Session identifier (uses current if not provided)

        Returns:
            Dict: Session details including:
                - sessionId, browserIdentifier, name
                - status (READY, TERMINATED)
                - createdAt, lastUpdatedAt
                - sessionTimeoutSeconds
                - sessionReplayArtifact (S3 location if recording enabled)
                - streams (automationStream, liveViewStream)
                - viewPort

        Example:
            >>> session_info = client.get_session()
            >>> print(f"Session status: {session_info['status']}")
            >>> if session_info.get('sessionReplayArtifact'):
            ...     print(f"Recording available at: {session_info['sessionReplayArtifact']}")
        """
        browser_id = browser_id or self.identifier
        session_id = session_id or self.session_id

        if not browser_id or not session_id:
            raise ValueError("Browser ID and Session ID must be provided or available from current session")

        self.logger.info("Getting session: %s", session_id)

        response = self.data_plane_client.get_browser_session(browserIdentifier=browser_id, sessionId=session_id)
        return response

    def list_sessions(
        self,
        browser_id: Optional[str] = None,
        status: Optional[str] = None,
        max_results: int = 10,
        next_token: Optional[str] = None,
    ) -> Dict:
        """List browser sessions for a specific browser.

        Args:
            browser_id (Optional[str]): Browser identifier (uses current if not provided)
            status (Optional[str]): Filter by status: "READY" or "TERMINATED"
            max_results (int): Maximum results (1-100, default 10)
            next_token (Optional[str]): Pagination token

        Returns:
            Dict: Response containing:
                - items (List[Dict]): List of session summaries
                - nextToken (str): Token for next page (if more results)

        Example:
            >>> # List all active sessions
            >>> response = client.list_sessions(status="READY")
            >>> for session in response['items']:
            ...     print(f"Session {session['sessionId']}: {session['status']}")
        """
        browser_id = browser_id or self.identifier
        if not browser_id:
            raise ValueError("Browser ID must be provided or available from current session")

        self.logger.info("Listing sessions for browser: %s", browser_id)

        request_params = {"browserIdentifier": browser_id, "maxResults": max_results}
        if status:
            request_params["status"] = status
        if next_token:
            request_params["nextToken"] = next_token

        response = self.data_plane_client.list_browser_sessions(**request_params)
        return response

    def update_stream(
        self,
        stream_status: str,
        browser_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> None:
        """Update the browser automation stream status.

        This is the new UpdateBrowserStream API for dynamic stream control.

        Args:
            stream_status (str): Status to set: "ENABLED" or "DISABLED"
            browser_id (Optional[str]): Browser identifier (uses current if not provided)
            session_id (Optional[str]): Session identifier (uses current if not provided)

        Example:
            >>> # Disable automation to take manual control
            >>> client.update_stream("DISABLED")
            >>> # Re-enable automation
            >>> client.update_stream("ENABLED")
        """
        browser_id = browser_id or self.identifier
        session_id = session_id or self.session_id

        if not browser_id or not session_id:
            raise ValueError("Browser ID and Session ID must be provided or available from current session")

        self.logger.info("Updating stream status to: %s", stream_status)

        self.data_plane_client.update_browser_stream(
            browserIdentifier=browser_id,
            sessionId=session_id,
            streamUpdate={"automationStreamUpdate": {"streamStatus": stream_status}},
        )

    def generate_ws_headers(self) -> Tuple[str, Dict[str, str]]:
        """Generate the WebSocket headers needed for connecting to the browser sandbox.

        Returns:
            Tuple[str, Dict[str, str]]: A tuple containing the WebSocket URL and headers.

        Raises:
            RuntimeError: If no AWS credentials are found.
        """
        self.logger.info("Generating websocket headers...")

        if not self.identifier or not self.session_id:
            self.start()

        host = get_data_plane_endpoint(self.region).replace("https://", "")
        path = f"/browser-streams/{self.identifier}/sessions/{self.session_id}/automation"
        ws_url = f"wss://{host}{path}"

        boto_session = boto3.Session()
        credentials = boto_session.get_credentials()
        if not credentials:
            raise RuntimeError("No AWS credentials found")

        frozen_credentials = credentials.get_frozen_credentials()

        request = AWSRequest(
            method="GET",
            url=f"https://{host}{path}",
            headers={
                "host": host,
                "x-amz-date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
            },
        )

        auth = SigV4Auth(frozen_credentials, "bedrock-agentcore", self.region)
        auth.add_auth(request)

        headers = {
            "Host": host,
            "X-Amz-Date": request.headers["x-amz-date"],
            "Authorization": request.headers["Authorization"],
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Version": "13",
            "Sec-WebSocket-Key": base64.b64encode(secrets.token_bytes(16)).decode(),
            "User-Agent": f"BrowserSandbox-Client/1.0 (Session: {self.session_id})",
        }

        if frozen_credentials.token:
            headers["X-Amz-Security-Token"] = frozen_credentials.token

        return ws_url, headers

    def generate_live_view_url(self, expires: int = DEFAULT_LIVE_VIEW_PRESIGNED_URL_TIMEOUT) -> str:
        """Generate a pre-signed URL for viewing the browser session.

        Args:
            expires (int): Seconds until URL expires (max 300).

        Returns:
            str: The pre-signed URL for viewing.

        Raises:
            ValueError: If expires exceeds maximum.
            RuntimeError: If URL generation fails.
        """
        self.logger.info("Generating live view url...")

        if expires > MAX_LIVE_VIEW_PRESIGNED_URL_TIMEOUT:
            raise ValueError(
                f"Expiry timeout cannot exceed {MAX_LIVE_VIEW_PRESIGNED_URL_TIMEOUT} seconds, got {expires}"
            )

        if not self.identifier or not self.session_id:
            self.start()

        url = urlparse(
            f"{get_data_plane_endpoint(self.region)}/browser-streams/{self.identifier}/sessions/{self.session_id}/live-view"
        )
        boto_session = boto3.Session()
        credentials = boto_session.get_credentials().get_frozen_credentials()
        request = AWSRequest(method="GET", url=url.geturl(), headers={"host": url.hostname})
        signer = SigV4QueryAuth(
            credentials=credentials, service_name="bedrock-agentcore", region_name=self.region, expires=expires
        )
        signer.add_auth(request)

        if not request.url:
            raise RuntimeError("Failed to generate live view url")

        return request.url

    def take_control(self):
        """Take control of the browser by disabling automation stream."""
        self.logger.info("Taking control of browser session...")

        if not self.identifier or not self.session_id:
            self.start()

        if not self.identifier or not self.session_id:
            raise RuntimeError("Could not find or start a browser session")

        self.update_stream("DISABLED")

    def release_control(self):
        """Release control by enabling automation stream."""
        self.logger.info("Releasing control of browser session...")

        if not self.identifier or not self.session_id:
            self.logger.warning("Could not find a browser session when releasing control")
            return

        self.update_stream("ENABLED")
```

#### `identifier`

Get the current browser identifier.

#### `session_id`

Get the current session ID.

#### `__init__(region)`

Initialize a Browser client for the specified AWS region.

Parameters:

| Name     | Type  | Description                                    | Default    |
| -------- | ----- | ---------------------------------------------- | ---------- |
| `region` | `str` | The AWS region to use for the Browser service. | *required* |

Source code in `bedrock_agentcore/tools/browser_client.py`

```
def __init__(self, region: str) -> None:
    """Initialize a Browser client for the specified AWS region.

    Args:
        region (str): The AWS region to use for the Browser service.
    """
    self.region = region
    self.logger = logging.getLogger(__name__)

    # Control plane client for browser management
    self.control_plane_client = boto3.client(
        "bedrock-agentcore-control",
        region_name=region,
        endpoint_url=get_control_plane_endpoint(region),
    )

    # Data plane client for session operations
    self.data_plane_client = boto3.client(
        "bedrock-agentcore",
        region_name=region,
        endpoint_url=get_data_plane_endpoint(region),
    )

    self._identifier = None
    self._session_id = None
```

#### `create_browser(name, execution_role_arn, network_configuration=None, description=None, recording=None, browser_signing=None, tags=None, client_token=None)`

Create a custom browser with specific configuration.

This is a control plane operation that provisions a new browser with custom settings including Web Bot Auth, VPC, and recording configuration.

Parameters:

| Name                    | Type                       | Description                                                                                                                                                            | Default    |
| ----------------------- | -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `name`                  | `str`                      | The name for the browser. Must match pattern a-zA-Z                                                                                                                    | *required* |
| `execution_role_arn`    | `str`                      | IAM role ARN with permissions for browser operations                                                                                                                   | *required* |
| `network_configuration` | `Optional[Dict]`           | Network configuration: { "networkMode": "PUBLIC" or "VPC", "vpcConfig": { # Required if networkMode is VPC "securityGroups": ["sg-xxx"], "subnets": ["subnet-xxx"] } } | `None`     |
| `description`           | `Optional[str]`            | Description of the browser (1-4096 chars)                                                                                                                              | `None`     |
| `recording`             | `Optional[Dict]`           | Recording configuration: { "enabled": True, "s3Location": { "bucket": "bucket-name", "keyPrefix": "path/prefix" } }                                                    | `None`     |
| `browser_signing`       | `Optional[Dict]`           | Web Bot Auth configuration (NEW FEATURE): { "enabled": True }                                                                                                          | `None`     |
| `tags`                  | `Optional[Dict[str, str]]` | Tags for the browser                                                                                                                                                   | `None`     |
| `client_token`          | `Optional[str]`            | Idempotency token                                                                                                                                                      | `None`     |

Returns:

| Name   | Type   | Description                                                                                                                                                                                                    |
| ------ | ------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Dict` | `Dict` | Response containing: - browserArn (str): ARN of created browser - browserId (str): Unique browser identifier - createdAt (datetime): Creation timestamp - status (str): Browser status (CREATING, READY, etc.) |

Example

> > > client = BrowserClient('us-west-2')
> > >
> > > ##### Create browser with Web Bot Auth enabled
> > >
> > > response = client.create_browser( ... name="my_signed_browser", ... execution_role_arn="arn:aws:iam::123456789012:role/BrowserRole", ... network_configuration={"networkMode": "PUBLIC"}, ... browser_signing={"enabled": True}, ... recording={ ... "enabled": True, ... "s3Location": { ... "bucket": "my-recordings", ... "keyPrefix": "browser-sessions/" ... } ... } ... ) browser_id = response['browserId']

Source code in `bedrock_agentcore/tools/browser_client.py`

```
def create_browser(
    self,
    name: str,
    execution_role_arn: str,
    network_configuration: Optional[Dict] = None,
    description: Optional[str] = None,
    recording: Optional[Dict] = None,
    browser_signing: Optional[Dict] = None,
    tags: Optional[Dict[str, str]] = None,
    client_token: Optional[str] = None,
) -> Dict:
    """Create a custom browser with specific configuration.

    This is a control plane operation that provisions a new browser with
    custom settings including Web Bot Auth, VPC, and recording configuration.

    Args:
        name (str): The name for the browser. Must match pattern [a-zA-Z][a-zA-Z0-9_]{0,47}
        execution_role_arn (str): IAM role ARN with permissions for browser operations
        network_configuration (Optional[Dict]): Network configuration:
            {
                "networkMode": "PUBLIC" or "VPC",
                "vpcConfig": {  # Required if networkMode is VPC
                    "securityGroups": ["sg-xxx"],
                    "subnets": ["subnet-xxx"]
                }
            }
        description (Optional[str]): Description of the browser (1-4096 chars)
        recording (Optional[Dict]): Recording configuration:
            {
                "enabled": True,
                "s3Location": {
                    "bucket": "bucket-name",
                    "keyPrefix": "path/prefix"
                }
            }
        browser_signing (Optional[Dict]): Web Bot Auth configuration (NEW FEATURE):
            {
                "enabled": True
            }
        tags (Optional[Dict[str, str]]): Tags for the browser
        client_token (Optional[str]): Idempotency token

    Returns:
        Dict: Response containing:
            - browserArn (str): ARN of created browser
            - browserId (str): Unique browser identifier
            - createdAt (datetime): Creation timestamp
            - status (str): Browser status (CREATING, READY, etc.)

    Example:
        >>> client = BrowserClient('us-west-2')
        >>> # Create browser with Web Bot Auth enabled
        >>> response = client.create_browser(
        ...     name="my_signed_browser",
        ...     execution_role_arn="arn:aws:iam::123456789012:role/BrowserRole",
        ...     network_configuration={"networkMode": "PUBLIC"},
        ...     browser_signing={"enabled": True},
        ...     recording={
        ...         "enabled": True,
        ...         "s3Location": {
        ...             "bucket": "my-recordings",
        ...             "keyPrefix": "browser-sessions/"
        ...         }
        ...     }
        ... )
        >>> browser_id = response['browserId']
    """
    self.logger.info("Creating browser: %s", name)

    request_params = {
        "name": name,
        "executionRoleArn": execution_role_arn,
        "networkConfiguration": network_configuration or {"networkMode": "PUBLIC"},
    }

    if description:
        request_params["description"] = description

    if recording:
        request_params["recording"] = recording

    if browser_signing:
        request_params["browserSigning"] = browser_signing
        self.logger.info("🔐 Web Bot Auth (browserSigning) enabled")

    if tags:
        request_params["tags"] = tags

    if client_token:
        request_params["clientToken"] = client_token

    response = self.control_plane_client.create_browser(**request_params)
    return response
```

#### `delete_browser(browser_id, client_token=None)`

Delete a custom browser.

Parameters:

| Name           | Type            | Description                      | Default    |
| -------------- | --------------- | -------------------------------- | ---------- |
| `browser_id`   | `str`           | The browser identifier to delete | *required* |
| `client_token` | `Optional[str]` | Idempotency token                | `None`     |

Returns:

| Name   | Type   | Description                                                                                                                                |
| ------ | ------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| `Dict` | `Dict` | Response containing: - browserId (str): ID of deleted browser - lastUpdatedAt (datetime): Update timestamp - status (str): Deletion status |

Example

> > > client.delete_browser("my-browser-abc123")

Source code in `bedrock_agentcore/tools/browser_client.py`

```
def delete_browser(self, browser_id: str, client_token: Optional[str] = None) -> Dict:
    """Delete a custom browser.

    Args:
        browser_id (str): The browser identifier to delete
        client_token (Optional[str]): Idempotency token

    Returns:
        Dict: Response containing:
            - browserId (str): ID of deleted browser
            - lastUpdatedAt (datetime): Update timestamp
            - status (str): Deletion status

    Example:
        >>> client.delete_browser("my-browser-abc123")
    """
    self.logger.info("Deleting browser: %s", browser_id)

    request_params = {"browserId": browser_id}
    if client_token:
        request_params["clientToken"] = client_token

    response = self.control_plane_client.delete_browser(**request_params)
    return response
```

#### `generate_live_view_url(expires=DEFAULT_LIVE_VIEW_PRESIGNED_URL_TIMEOUT)`

Generate a pre-signed URL for viewing the browser session.

Parameters:

| Name      | Type  | Description                          | Default                                   |
| --------- | ----- | ------------------------------------ | ----------------------------------------- |
| `expires` | `int` | Seconds until URL expires (max 300). | `DEFAULT_LIVE_VIEW_PRESIGNED_URL_TIMEOUT` |

Returns:

| Name  | Type  | Description                     |
| ----- | ----- | ------------------------------- |
| `str` | `str` | The pre-signed URL for viewing. |

Raises:

| Type           | Description                 |
| -------------- | --------------------------- |
| `ValueError`   | If expires exceeds maximum. |
| `RuntimeError` | If URL generation fails.    |

Source code in `bedrock_agentcore/tools/browser_client.py`

```
def generate_live_view_url(self, expires: int = DEFAULT_LIVE_VIEW_PRESIGNED_URL_TIMEOUT) -> str:
    """Generate a pre-signed URL for viewing the browser session.

    Args:
        expires (int): Seconds until URL expires (max 300).

    Returns:
        str: The pre-signed URL for viewing.

    Raises:
        ValueError: If expires exceeds maximum.
        RuntimeError: If URL generation fails.
    """
    self.logger.info("Generating live view url...")

    if expires > MAX_LIVE_VIEW_PRESIGNED_URL_TIMEOUT:
        raise ValueError(
            f"Expiry timeout cannot exceed {MAX_LIVE_VIEW_PRESIGNED_URL_TIMEOUT} seconds, got {expires}"
        )

    if not self.identifier or not self.session_id:
        self.start()

    url = urlparse(
        f"{get_data_plane_endpoint(self.region)}/browser-streams/{self.identifier}/sessions/{self.session_id}/live-view"
    )
    boto_session = boto3.Session()
    credentials = boto_session.get_credentials().get_frozen_credentials()
    request = AWSRequest(method="GET", url=url.geturl(), headers={"host": url.hostname})
    signer = SigV4QueryAuth(
        credentials=credentials, service_name="bedrock-agentcore", region_name=self.region, expires=expires
    )
    signer.add_auth(request)

    if not request.url:
        raise RuntimeError("Failed to generate live view url")

    return request.url
```

#### `generate_ws_headers()`

Generate the WebSocket headers needed for connecting to the browser sandbox.

Returns:

| Type                         | Description                                                                     |
| ---------------------------- | ------------------------------------------------------------------------------- |
| `Tuple[str, Dict[str, str]]` | Tuple\[str, Dict[str, str]\]: A tuple containing the WebSocket URL and headers. |

Raises:

| Type           | Description                      |
| -------------- | -------------------------------- |
| `RuntimeError` | If no AWS credentials are found. |

Source code in `bedrock_agentcore/tools/browser_client.py`

```
def generate_ws_headers(self) -> Tuple[str, Dict[str, str]]:
    """Generate the WebSocket headers needed for connecting to the browser sandbox.

    Returns:
        Tuple[str, Dict[str, str]]: A tuple containing the WebSocket URL and headers.

    Raises:
        RuntimeError: If no AWS credentials are found.
    """
    self.logger.info("Generating websocket headers...")

    if not self.identifier or not self.session_id:
        self.start()

    host = get_data_plane_endpoint(self.region).replace("https://", "")
    path = f"/browser-streams/{self.identifier}/sessions/{self.session_id}/automation"
    ws_url = f"wss://{host}{path}"

    boto_session = boto3.Session()
    credentials = boto_session.get_credentials()
    if not credentials:
        raise RuntimeError("No AWS credentials found")

    frozen_credentials = credentials.get_frozen_credentials()

    request = AWSRequest(
        method="GET",
        url=f"https://{host}{path}",
        headers={
            "host": host,
            "x-amz-date": datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        },
    )

    auth = SigV4Auth(frozen_credentials, "bedrock-agentcore", self.region)
    auth.add_auth(request)

    headers = {
        "Host": host,
        "X-Amz-Date": request.headers["x-amz-date"],
        "Authorization": request.headers["Authorization"],
        "Upgrade": "websocket",
        "Connection": "Upgrade",
        "Sec-WebSocket-Version": "13",
        "Sec-WebSocket-Key": base64.b64encode(secrets.token_bytes(16)).decode(),
        "User-Agent": f"BrowserSandbox-Client/1.0 (Session: {self.session_id})",
    }

    if frozen_credentials.token:
        headers["X-Amz-Security-Token"] = frozen_credentials.token

    return ws_url, headers
```

#### `get_browser(browser_id)`

Get detailed information about a browser.

Parameters:

| Name         | Type  | Description            | Default    |
| ------------ | ----- | ---------------------- | ---------- |
| `browser_id` | `str` | The browser identifier | *required* |

Returns:

| Name   | Type   | Description                                                                                                                                                                                                                                                                                            |
| ------ | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Dict` | `Dict` | Browser details including: - browserArn, browserId, name, description - createdAt, lastUpdatedAt - executionRoleArn - networkConfiguration - recording configuration - browserSigning configuration (if enabled) - status (CREATING, CREATE_FAILED, READY, DELETING, etc.) - failureReason (if failed) |

Example

> > > browser_info = client.get_browser("my-browser-abc123") print(f"Status: {browser_info['status']}") if browser_info.get('browserSigning'): ... print("Web Bot Auth is enabled!")

Source code in `bedrock_agentcore/tools/browser_client.py`

```
def get_browser(self, browser_id: str) -> Dict:
    """Get detailed information about a browser.

    Args:
        browser_id (str): The browser identifier

    Returns:
        Dict: Browser details including:
            - browserArn, browserId, name, description
            - createdAt, lastUpdatedAt
            - executionRoleArn
            - networkConfiguration
            - recording configuration
            - browserSigning configuration (if enabled)
            - status (CREATING, CREATE_FAILED, READY, DELETING, etc.)
            - failureReason (if failed)

    Example:
        >>> browser_info = client.get_browser("my-browser-abc123")
        >>> print(f"Status: {browser_info['status']}")
        >>> if browser_info.get('browserSigning'):
        ...     print("Web Bot Auth is enabled!")
    """
    self.logger.info("Getting browser: %s", browser_id)
    response = self.control_plane_client.get_browser(browserId=browser_id)
    return response
```

#### `get_session(browser_id=None, session_id=None)`

Get detailed information about a browser session.

Parameters:

| Name         | Type            | Description                                       | Default |
| ------------ | --------------- | ------------------------------------------------- | ------- |
| `browser_id` | `Optional[str]` | Browser identifier (uses current if not provided) | `None`  |
| `session_id` | `Optional[str]` | Session identifier (uses current if not provided) | `None`  |

Returns:

| Name   | Type   | Description                                                                                                                                                                                                                                                        |
| ------ | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Dict` | `Dict` | Session details including: - sessionId, browserIdentifier, name - status (READY, TERMINATED) - createdAt, lastUpdatedAt - sessionTimeoutSeconds - sessionReplayArtifact (S3 location if recording enabled) - streams (automationStream, liveViewStream) - viewPort |

Example

> > > session_info = client.get_session() print(f"Session status: {session_info['status']}") if session_info.get('sessionReplayArtifact'): ... print(f"Recording available at: {session_info['sessionReplayArtifact']}")

Source code in `bedrock_agentcore/tools/browser_client.py`

```
def get_session(self, browser_id: Optional[str] = None, session_id: Optional[str] = None) -> Dict:
    """Get detailed information about a browser session.

    Args:
        browser_id (Optional[str]): Browser identifier (uses current if not provided)
        session_id (Optional[str]): Session identifier (uses current if not provided)

    Returns:
        Dict: Session details including:
            - sessionId, browserIdentifier, name
            - status (READY, TERMINATED)
            - createdAt, lastUpdatedAt
            - sessionTimeoutSeconds
            - sessionReplayArtifact (S3 location if recording enabled)
            - streams (automationStream, liveViewStream)
            - viewPort

    Example:
        >>> session_info = client.get_session()
        >>> print(f"Session status: {session_info['status']}")
        >>> if session_info.get('sessionReplayArtifact'):
        ...     print(f"Recording available at: {session_info['sessionReplayArtifact']}")
    """
    browser_id = browser_id or self.identifier
    session_id = session_id or self.session_id

    if not browser_id or not session_id:
        raise ValueError("Browser ID and Session ID must be provided or available from current session")

    self.logger.info("Getting session: %s", session_id)

    response = self.data_plane_client.get_browser_session(browserIdentifier=browser_id, sessionId=session_id)
    return response
```

#### `list_browsers(browser_type=None, max_results=10, next_token=None)`

List all browsers in the account.

Parameters:

| Name           | Type            | Description                                   | Default |
| -------------- | --------------- | --------------------------------------------- | ------- |
| `browser_type` | `Optional[str]` | Filter by type: "SYSTEM" or "CUSTOM"          | `None`  |
| `max_results`  | `int`           | Maximum results to return (1-100, default 10) | `10`    |
| `next_token`   | `Optional[str]` | Token for pagination                          | `None`  |

Returns:

| Name   | Type   | Description                                                                                                                              |
| ------ | ------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `Dict` | `Dict` | Response containing: - browserSummaries (List[Dict]): List of browser summaries - nextToken (str): Token for next page (if more results) |

Example

> > > ##### List all custom browsers
> > >
> > > response = client.list_browsers(browser_type="CUSTOM") for browser in response\['browserSummaries'\]: ... print(f"{browser['name']}: {browser['status']}")

Source code in `bedrock_agentcore/tools/browser_client.py`

```
def list_browsers(
    self,
    browser_type: Optional[str] = None,
    max_results: int = 10,
    next_token: Optional[str] = None,
) -> Dict:
    """List all browsers in the account.

    Args:
        browser_type (Optional[str]): Filter by type: "SYSTEM" or "CUSTOM"
        max_results (int): Maximum results to return (1-100, default 10)
        next_token (Optional[str]): Token for pagination

    Returns:
        Dict: Response containing:
            - browserSummaries (List[Dict]): List of browser summaries
            - nextToken (str): Token for next page (if more results)

    Example:
        >>> # List all custom browsers
        >>> response = client.list_browsers(browser_type="CUSTOM")
        >>> for browser in response['browserSummaries']:
        ...     print(f"{browser['name']}: {browser['status']}")
    """
    self.logger.info("Listing browsers (type=%s)", browser_type)

    request_params = {"maxResults": max_results}
    if browser_type:
        request_params["type"] = browser_type
    if next_token:
        request_params["nextToken"] = next_token

    response = self.control_plane_client.list_browsers(**request_params)
    return response
```

#### `list_sessions(browser_id=None, status=None, max_results=10, next_token=None)`

List browser sessions for a specific browser.

Parameters:

| Name          | Type            | Description                                       | Default |
| ------------- | --------------- | ------------------------------------------------- | ------- |
| `browser_id`  | `Optional[str]` | Browser identifier (uses current if not provided) | `None`  |
| `status`      | `Optional[str]` | Filter by status: "READY" or "TERMINATED"         | `None`  |
| `max_results` | `int`           | Maximum results (1-100, default 10)               | `10`    |
| `next_token`  | `Optional[str]` | Pagination token                                  | `None`  |

Returns:

| Name   | Type   | Description                                                                                                                   |
| ------ | ------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `Dict` | `Dict` | Response containing: - items (List[Dict]): List of session summaries - nextToken (str): Token for next page (if more results) |

Example

> > > ##### List all active sessions
> > >
> > > response = client.list_sessions(status="READY") for session in response\['items'\]: ... print(f"Session {session['sessionId']}: {session['status']}")

Source code in `bedrock_agentcore/tools/browser_client.py`

```
def list_sessions(
    self,
    browser_id: Optional[str] = None,
    status: Optional[str] = None,
    max_results: int = 10,
    next_token: Optional[str] = None,
) -> Dict:
    """List browser sessions for a specific browser.

    Args:
        browser_id (Optional[str]): Browser identifier (uses current if not provided)
        status (Optional[str]): Filter by status: "READY" or "TERMINATED"
        max_results (int): Maximum results (1-100, default 10)
        next_token (Optional[str]): Pagination token

    Returns:
        Dict: Response containing:
            - items (List[Dict]): List of session summaries
            - nextToken (str): Token for next page (if more results)

    Example:
        >>> # List all active sessions
        >>> response = client.list_sessions(status="READY")
        >>> for session in response['items']:
        ...     print(f"Session {session['sessionId']}: {session['status']}")
    """
    browser_id = browser_id or self.identifier
    if not browser_id:
        raise ValueError("Browser ID must be provided or available from current session")

    self.logger.info("Listing sessions for browser: %s", browser_id)

    request_params = {"browserIdentifier": browser_id, "maxResults": max_results}
    if status:
        request_params["status"] = status
    if next_token:
        request_params["nextToken"] = next_token

    response = self.data_plane_client.list_browser_sessions(**request_params)
    return response
```

#### `release_control()`

Release control by enabling automation stream.

Source code in `bedrock_agentcore/tools/browser_client.py`

```
def release_control(self):
    """Release control by enabling automation stream."""
    self.logger.info("Releasing control of browser session...")

    if not self.identifier or not self.session_id:
        self.logger.warning("Could not find a browser session when releasing control")
        return

    self.update_stream("ENABLED")
```

#### `start(identifier=DEFAULT_IDENTIFIER, name=None, session_timeout_seconds=DEFAULT_SESSION_TIMEOUT, viewport=None)`

Start a browser sandbox session.

This method initializes a new browser session with the provided parameters.

Parameters:

| Name                      | Type                       | Description                                                                                                  | Default                   |
| ------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------- |
| `identifier`              | `Optional[str]`            | The browser sandbox identifier to use. Can be DEFAULT_IDENTIFIER or a custom browser ID from create_browser. | `DEFAULT_IDENTIFIER`      |
| `name`                    | `Optional[str]`            | A name for this session.                                                                                     | `None`                    |
| `session_timeout_seconds` | `Optional[int]`            | The timeout for the session in seconds. Range: 1-28800 (8 hours). Default: 3600 (1 hour).                    | `DEFAULT_SESSION_TIMEOUT` |
| `viewport`                | `Optional[Dict[str, int]]` | The viewport dimensions:                                                                                     | `None`                    |

Returns:

| Name  | Type  | Description                                  |
| ----- | ----- | -------------------------------------------- |
| `str` | `str` | The session ID of the newly created session. |

Example

> > > ##### Use system browser
> > >
> > > session_id = client.start()
> > >
> > > ##### Use custom browser with Web Bot Auth
> > >
> > > session_id = client.start( ... identifier="my-browser-abc123", ... viewport={'width': 1920, 'height': 1080}, ... session_timeout_seconds=7200 # 2 hours ... )

Source code in `bedrock_agentcore/tools/browser_client.py`

```
def start(
    self,
    identifier: Optional[str] = DEFAULT_IDENTIFIER,
    name: Optional[str] = None,
    session_timeout_seconds: Optional[int] = DEFAULT_SESSION_TIMEOUT,
    viewport: Optional[Dict[str, int]] = None,
) -> str:
    """Start a browser sandbox session.

    This method initializes a new browser session with the provided parameters.

    Args:
        identifier (Optional[str]): The browser sandbox identifier to use.
            Can be DEFAULT_IDENTIFIER or a custom browser ID from create_browser.
        name (Optional[str]): A name for this session.
        session_timeout_seconds (Optional[int]): The timeout for the session in seconds.
            Range: 1-28800 (8 hours). Default: 3600 (1 hour).
        viewport (Optional[Dict[str, int]]): The viewport dimensions:
            {'width': 1920, 'height': 1080}

    Returns:
        str: The session ID of the newly created session.

    Example:
        >>> # Use system browser
        >>> session_id = client.start()
        >>>
        >>> # Use custom browser with Web Bot Auth
        >>> session_id = client.start(
        ...     identifier="my-browser-abc123",
        ...     viewport={'width': 1920, 'height': 1080},
        ...     session_timeout_seconds=7200  # 2 hours
        ... )
    """
    self.logger.info("Starting browser session...")

    request_params = {
        "browserIdentifier": identifier,
        "name": name or f"browser-session-{uuid.uuid4().hex[:8]}",
        "sessionTimeoutSeconds": session_timeout_seconds,
    }

    if viewport is not None:
        request_params["viewPort"] = viewport

    response = self.data_plane_client.start_browser_session(**request_params)

    self.identifier = response["browserIdentifier"]
    self.session_id = response["sessionId"]

    self.logger.info("✅ Session started: %s", self.session_id)
    return self.session_id
```

#### `stop()`

Stop the current browser session if one is active.

Returns:

| Name   | Type   | Description                                  |
| ------ | ------ | -------------------------------------------- |
| `bool` | `bool` | True if successful or no session was active. |

Source code in `bedrock_agentcore/tools/browser_client.py`

```
def stop(self) -> bool:
    """Stop the current browser session if one is active.

    Returns:
        bool: True if successful or no session was active.
    """
    self.logger.info("Stopping browser session...")

    if not self.session_id or not self.identifier:
        return True

    self.data_plane_client.stop_browser_session(browserIdentifier=self.identifier, sessionId=self.session_id)

    self.logger.info("✅ Session stopped: %s", self.session_id)
    self.identifier = None
    self.session_id = None
    return True
```

#### `take_control()`

Take control of the browser by disabling automation stream.

Source code in `bedrock_agentcore/tools/browser_client.py`

```
def take_control(self):
    """Take control of the browser by disabling automation stream."""
    self.logger.info("Taking control of browser session...")

    if not self.identifier or not self.session_id:
        self.start()

    if not self.identifier or not self.session_id:
        raise RuntimeError("Could not find or start a browser session")

    self.update_stream("DISABLED")
```

#### `update_stream(stream_status, browser_id=None, session_id=None)`

Update the browser automation stream status.

This is the new UpdateBrowserStream API for dynamic stream control.

Parameters:

| Name            | Type            | Description                                       | Default    |
| --------------- | --------------- | ------------------------------------------------- | ---------- |
| `stream_status` | `str`           | Status to set: "ENABLED" or "DISABLED"            | *required* |
| `browser_id`    | `Optional[str]` | Browser identifier (uses current if not provided) | `None`     |
| `session_id`    | `Optional[str]` | Session identifier (uses current if not provided) | `None`     |

Example

> > > ##### Disable automation to take manual control
> > >
> > > client.update_stream("DISABLED")
> > >
> > > ##### Re-enable automation
> > >
> > > client.update_stream("ENABLED")

Source code in `bedrock_agentcore/tools/browser_client.py`

```
def update_stream(
    self,
    stream_status: str,
    browser_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> None:
    """Update the browser automation stream status.

    This is the new UpdateBrowserStream API for dynamic stream control.

    Args:
        stream_status (str): Status to set: "ENABLED" or "DISABLED"
        browser_id (Optional[str]): Browser identifier (uses current if not provided)
        session_id (Optional[str]): Session identifier (uses current if not provided)

    Example:
        >>> # Disable automation to take manual control
        >>> client.update_stream("DISABLED")
        >>> # Re-enable automation
        >>> client.update_stream("ENABLED")
    """
    browser_id = browser_id or self.identifier
    session_id = session_id or self.session_id

    if not browser_id or not session_id:
        raise ValueError("Browser ID and Session ID must be provided or available from current session")

    self.logger.info("Updating stream status to: %s", stream_status)

    self.data_plane_client.update_browser_stream(
        browserIdentifier=browser_id,
        sessionId=session_id,
        streamUpdate={"automationStreamUpdate": {"streamStatus": stream_status}},
    )
```

### `browser_session(region, viewport=None, identifier=None)`

Context manager for creating and managing a browser sandbox session.

Parameters:

| Name         | Type                       | Description                            | Default    |
| ------------ | -------------------------- | -------------------------------------- | ---------- |
| `region`     | `str`                      | AWS region.                            | *required* |
| `viewport`   | `Optional[Dict[str, int]]` | Viewport dimensions.                   | `None`     |
| `identifier` | `Optional[str]`            | Browser identifier (system or custom). | `None`     |

Yields:

| Name            | Type            | Description                                |
| --------------- | --------------- | ------------------------------------------ |
| `BrowserClient` | `BrowserClient` | An initialized and started browser client. |

Example

> > > #### Use system browser
> > >
> > > with browser_session('us-west-2') as client: ... ws_url, headers = client.generate_ws_headers() ...
> > >
> > > #### Use custom browser with Web Bot Auth
> > >
> > > with browser_session('us-west-2', identifier='my-signed-browser') as client: ... # Automation with reduced CAPTCHA friction ... pass

Source code in `bedrock_agentcore/tools/browser_client.py`

```
@contextmanager
def browser_session(
    region: str, viewport: Optional[Dict[str, int]] = None, identifier: Optional[str] = None
) -> Generator[BrowserClient, None, None]:
    """Context manager for creating and managing a browser sandbox session.

    Args:
        region (str): AWS region.
        viewport (Optional[Dict[str, int]]): Viewport dimensions.
        identifier (Optional[str]): Browser identifier (system or custom).

    Yields:
        BrowserClient: An initialized and started browser client.

    Example:
        >>> # Use system browser
        >>> with browser_session('us-west-2') as client:
        ...     ws_url, headers = client.generate_ws_headers()
        ...
        >>> # Use custom browser with Web Bot Auth
        >>> with browser_session('us-west-2', identifier='my-signed-browser') as client:
        ...     # Automation with reduced CAPTCHA friction
        ...     pass
    """
    client = BrowserClient(region)
    start_kwargs = {}
    if viewport is not None:
        start_kwargs["viewport"] = viewport
    if identifier is not None:
        start_kwargs["identifier"] = identifier

    client.start(**start_kwargs)

    try:
        yield client
    finally:
        client.stop()
```
