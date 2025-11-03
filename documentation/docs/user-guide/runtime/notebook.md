# Jupyter Notebook Support

The AgentCore Runtime provides Jupyter notebook support for quick experimentation and testing using the new **code_zip deployment mode**.

## What is Code Zip Deployment?

**Code Zip** is the new default and preferred deployment method for AgentCore Runtime:

- ✅ **No Docker required** - Deploy Python code directly to runtime
- ✅ **Faster deployments** - Skip container build process
- ✅ **Simpler setup** - Works out of the box in notebooks
- ✅ **Better local testing** - Run agents locally with `uv run`
- ✅ **Full feature parity** - All AgentCore features supported

## Basic Example

```python
# Import the notebook Runtime class
from bedrock_agentcore_starter_toolkit.notebook import Runtime

# Initialize
runtime = Runtime()

# Configure your agent (uses code_zip by default)
config = runtime.configure(
    entrypoint="my_agent.py",
    auto_create_execution_role=True,
    auto_create_s3=True,
    deployment_type="code_zip",  # Default
    runtime_type="PYTHON_3_11"  # Auto-detected
)

# Deploy to cloud
result = runtime.launch()
print(f"Agent ARN: {result.agent_arn}")

# Test your agent
response = runtime.invoke({"prompt": "Hello from notebook!"})
print(response)

# Clean up when done
runtime.destroy()
```

## Code Zip vs Container Deployment

### Code Zip (Default & Recommended)

```python
# Simple code_zip deployment
runtime.configure(
    entrypoint="my_agent.py",
    auto_create_execution_role=True,
    deployment_type="code_zip",  # Default
    runtime_type="PYTHON_3_11"
)
```

**Benefits:**
- ✅ No Docker required
- ✅ Faster deployments
- ✅ Simpler debugging
- ✅ Works in any notebook environment

### Container Deployment (Legacy)

```python
# Container deployment for complex cases
runtime.configure(
    entrypoint="my_agent.py",
    auto_create_execution_role=True,
    auto_create_ecr=True,
    deployment_type="container"
)
```

**Use when you need:**
- Complex system dependencies
- Large applications (>250MB)
- Custom base images
- Any Python runtime version

## Simple Agent Example

Create a simple agent file first:

```python
# my_agent.py
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

app = BedrockAgentCoreApp()
agent = Agent()

@app.entrypoint
def invoke(payload):
    """Your AI agent function"""
    user_message = payload.get("prompt", "Hello! How can I help you today?")
    result = agent(user_message)
    return {"result": result.message}

if __name__ == "__main__":
    app.run()
```

Create `requirements.txt`:

```
bedrock-agentcore
strands-agents
aws-opentelemetry-distro
```

## Complete Workflow Example

```python
from bedrock_agentcore_starter_toolkit.notebook import Runtime

# Initialize runtime
runtime = Runtime()

# Step 1: Configure agent
print("🔧 Configuring agent...")
config = runtime.configure(
    entrypoint="my_agent.py",
    agent_name="my-notebook-agent",
    auto_create_execution_role=True,
    auto_create_s3=True,
    memory_mode="STM_ONLY",  # or "STM_AND_LTM" or "NO_MEMORY"
    deployment_type="code_zip",  # Default
    runtime_type="PYTHON_3_11"  # Auto-detected
)

# Step 2: Test locally (optional)
print("🏠 Testing locally...")
local_result = runtime.launch(local=True)
response = runtime.invoke({"prompt": "Hello local!"}, local=True)
print(f"Local response: {response}")

# Step 3: Deploy to cloud
print("🚀 Deploying to cloud...")
cloud_result = runtime.launch()
print(f"Agent ARN: {cloud_result.agent_arn}")

# Step 4: Test cloud deployment
print("☁️ Testing cloud deployment...")
response = runtime.invoke({"prompt": "Hello cloud!"})
print(f"Cloud response: {response}")

# Step 5: Check status
print("📊 Checking status...")
status = runtime.status()
print(f"Agent: {status.config.name}")
print(f"Memory: {status.memory_status}")

# Step 6: Clean up
print("🗑️ Cleaning up...")
destroy_result = runtime.destroy()
print(f"Removed {len(destroy_result.resources_removed)} resources")
```

## Configuration Options

The notebook API supports all the same options as the CLI:

```python
runtime.configure(
    entrypoint="my_agent.py",
    agent_name="my-agent",

    # AWS Configuration
    execution_role="arn:aws:iam::123456789012:role/MyRole",  # or auto_create_execution_role=True
    region="us-west-2",

    # Deployment Configuration
    deployment_type="code_zip",  # or "container"
    runtime_type="PYTHON_3_11",  # Auto-detected for code_zip

    # S3 Configuration (code_zip only)
    s3_path="s3://my-bucket/agents/",  # or auto_create_s3=True
    auto_create_s3=True,

    # ECR Configuration (container only)
    ecr_repository="my-ecr-repo",  # or auto_create_ecr=True
    auto_create_ecr=True,

    # Memory Configuration
    memory_mode="STM_ONLY",  # "NO_MEMORY", "STM_ONLY", "STM_AND_LTM"

    # Networking (optional)
    vpc_enabled=False,
    vpc_subnets=["subnet-123", "subnet-456"],  # Required if vpc_enabled=True
    vpc_security_groups=["sg-789"],  # Required if vpc_enabled=True

    # Observability
    disable_otel=False,  # Enable OpenTelemetry by default

    # Lifecycle (optional)
    idle_timeout=900,  # seconds
    max_lifetime=28800,  # seconds

    # Authentication (optional)
    authorizer_configuration={"type": "JWT", "issuer": "..."},
    request_header_configuration={"allowlist": ["Authorization"]},

    # Other
    requirements=["numpy", "pandas"],  # Generate requirements.txt
    requirements_file="requirements.txt",  # Use existing file
    non_interactive=True  # Skip prompts
)
```

## Launch Options

```python
# Cloud deployment (default)
result = runtime.launch()

# Local development
result = runtime.launch(local=True)

# Local build + cloud deploy (container only)
result = runtime.launch(local_build=True)

# With environment variables
result = runtime.launch(env_vars={"DEBUG": "true"})

# Auto-update on conflicts
result = runtime.launch(auto_update_on_conflict=True)
```

## Invoke Options

```python
# Basic invoke
response = runtime.invoke({"prompt": "Hello!"})

# With session ID for memory
response = runtime.invoke(
    {"prompt": "Remember my name is Alice"},
    session_id="user-123"
)

# Local invoke
response = runtime.invoke({"prompt": "Hello!"}, local=True)

# With authentication
response = runtime.invoke(
    {"prompt": "Hello!"},
    bearer_token="jwt-token",
    user_id="user-123"
)
```

## Error Handling

```python
try:
    runtime.configure(
        entrypoint="my_agent.py",
        deployment_type="code_zip",
        runtime_type="PYTHON_3_15"  # Unsupported version
    )
except ValueError as e:
    print(f"Configuration error: {e}")

try:
    result = runtime.launch(local=True, local_build=True)  # Invalid combination
except ValueError as e:
    print(f"Launch error: {e}")
```

## Best Practices

### For Development
```python
# Quick iteration cycle
runtime.configure(entrypoint="my_agent.py", auto_create_execution_role=True)
runtime.launch(local=True)  # Fast local testing
runtime.invoke({"prompt": "test"}, local=True)
```

### For Production
```python
# Production-ready configuration
runtime.configure(
    entrypoint="my_agent.py",
    execution_role="arn:aws:iam::123456789012:role/ProdRole",
    memory_mode="STM_AND_LTM",
    deployment_type="code_zip",
    region="us-west-2"
)
runtime.launch()  # Deploy to cloud
```

### For Complex Applications
```python
# Use container deployment for complex needs
runtime.configure(
    entrypoint="my_agent.py",
    deployment_type="container",  # For large/complex apps
    auto_create_execution_role=True,
    auto_create_ecr=True
)
```

Then use it in your notebook:

```python
from bedrock_agentcore_starter_toolkit.notebook import Runtime

runtime = Runtime()

# Configure
runtime.configure(
    entrypoint="my_agent.py",
    execution_role="arn:aws:iam::123456789012:role/MyRole"
)

# Launch locally for testing
runtime.launch(local=True)

# Test the agent
response = runtime.invoke({"prompt": "Test from notebook"})
print(response)  # {"result": "You said: Test from notebook"}
```

## Available Methods

- **`configure()`** - Set up agent configuration
- **`launch(local=True)`** - Build and run locally
- **`invoke(payload)`** - Test your agent
- **`status()`** - Check agent status

## Limitations

- **Local testing focus** - Not optimized for production workflows
- **Basic error handling** - Limited error reporting compared to CLI
- **Configuration limitations** - Fewer options than full CLI interface
- **No interactive prompts** - All configuration must be provided programmatically

For full-featured development and production deployment, use the [AgentCore CLI](../../api-reference/runtime-cli.md) instead.
