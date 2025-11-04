# Jupyter Notebook Support

!!! warning "Local Testing Only"

    The notebook interface is intended for **local development and testing only**. It has rough edges and is not recommended for production use. For production deployment, use the Boto3 SDK instead.

The AgentCore Runtime provides basic Jupyter notebook support for quick experimentation and testing.

## Basic Example

```python
# Import the notebook Runtime class
from bedrock_agentcore_starter_toolkit.notebook import Runtime

# Initialize
runtime = Runtime()

# Configure your agent
config = runtime.configure(
    entrypoint="my_agent.py",
    execution_role="arn:aws:iam::123456789012:role/MyExecutionRole"
)

# Test locally
local_result = runtime.launch(local=True)
print(f"Local container: {local_result.tag}")

# Test your agent
response = runtime.invoke({"prompt": "Hello from notebook!"})
print(response)
```

## Simple Agent Example

Create a simple agent file first:

```python
# my_agent.py
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def handler(payload):
    prompt = payload.get("prompt", "Hello")
    return {"result": f"You said: {prompt}"}

if __name__ == "__main__":
    app.run()
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
