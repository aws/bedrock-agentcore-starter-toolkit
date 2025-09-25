# Runtime

Runtime management and application context for Bedrock AgentCore.

## `bedrock_agentcore.runtime`

BedrockAgentCore Runtime Package.

This package contains the core runtime components for Bedrock AgentCore applications:

- BedrockAgentCoreApp: Main application class
- RequestContext: HTTP request context
- BedrockAgentCoreContext: Agent identity context

### `BedrockAgentCoreApp`

Bases: `Starlette`

Bedrock AgentCore application class that extends Starlette for AI agent deployment.

Source code in `bedrock_agentcore/runtime/app.py`

```
class BedrockAgentCoreApp(Starlette):
    """Bedrock AgentCore application class that extends Starlette for AI agent deployment."""

    def __init__(self, debug: bool = False, lifespan: Optional[Lifespan] = None):
        """Initialize Bedrock AgentCore application.

        Args:
            debug: Enable debug actions for task management (default: False)
            lifespan: Optional lifespan context manager for startup/shutdown
        """
        self.handlers: Dict[str, Callable] = {}
        self._ping_handler: Optional[Callable] = None
        self._active_tasks: Dict[int, Dict[str, Any]] = {}
        self._task_counter_lock: threading.Lock = threading.Lock()
        self._forced_ping_status: Optional[PingStatus] = None
        self._last_status_update_time: float = time.time()

        routes = [
            Route("/invocations", self._handle_invocation, methods=["POST"]),
            Route("/ping", self._handle_ping, methods=["GET"]),
        ]
        super().__init__(routes=routes, lifespan=lifespan)
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

            return RequestContext(session_id=session_id, request_headers=req_headers)
        except Exception as e:
            self.logger.warning("Failed to build request context: %s: %s", type(e).__name__, e)
            request_id = str(uuid.uuid4())
            BedrockAgentCoreContext.set_request_context(request_id, None)
            return RequestContext(session_id=None)

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

#### `__init__(debug=False, lifespan=None)`

Initialize Bedrock AgentCore application.

Parameters:

| Name       | Type                 | Description                                               | Default |
| ---------- | -------------------- | --------------------------------------------------------- | ------- |
| `debug`    | `bool`               | Enable debug actions for task management (default: False) | `False` |
| `lifespan` | `Optional[Lifespan]` | Optional lifespan context manager for startup/shutdown    | `None`  |

Source code in `bedrock_agentcore/runtime/app.py`

```
def __init__(self, debug: bool = False, lifespan: Optional[Lifespan] = None):
    """Initialize Bedrock AgentCore application.

    Args:
        debug: Enable debug actions for task management (default: False)
        lifespan: Optional lifespan context manager for startup/shutdown
    """
    self.handlers: Dict[str, Callable] = {}
    self._ping_handler: Optional[Callable] = None
    self._active_tasks: Dict[int, Dict[str, Any]] = {}
    self._task_counter_lock: threading.Lock = threading.Lock()
    self._forced_ping_status: Optional[PingStatus] = None
    self._last_status_update_time: float = time.time()

    routes = [
        Route("/invocations", self._handle_invocation, methods=["POST"]),
        Route("/ping", self._handle_ping, methods=["GET"]),
    ]
    super().__init__(routes=routes, lifespan=lifespan)
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

### `BedrockAgentCoreContext`

Unified context manager for Bedrock AgentCore.

Source code in `bedrock_agentcore/runtime/context.py`

```
class BedrockAgentCoreContext:
    """Unified context manager for Bedrock AgentCore."""

    _workload_access_token: ContextVar[Optional[str]] = ContextVar("workload_access_token")
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
```
