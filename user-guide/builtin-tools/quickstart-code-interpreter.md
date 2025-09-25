# Getting Started with Code Interpreter

The Amazon Bedrock AgentCore Code Interpreter provides a secure environment for executing code snippets directly within your agent applications. This guide will help you get started with implementing code execution capabilities in your agents.

## Prerequisites

Before using the Code Interpreter, ensure you have:

- An AWS account with appropriate permissions
- Python 3.10+ installed

## Install the SDK

```
pip install bedrock-agentcore
```

## Create a Code Interpreter Session

The bedrock-agentcore SDK provides a convenient way to create code interpreter sessions using the managed code interpreter `aws.codeinterpreter.v1`:

```
from bedrock_agentcore.tools.code_interpreter_client import code_session

# Create a code interpreter session using the context manager
with code_session("us-west-2") as client:
    # The session is automatically created and managed
    print(f"Code interpreter session created")

    # List files in the session
    result = client.invoke("listFiles")
    for event in result["stream"]:
        print(event["result"]["content"])

# The session is automatically closed when exiting the context manager
```

If you need more control over the session lifecycle, you can also use the client without a context manager:

```
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter

# Create a code interpreter client
client = CodeInterpreter(region="us-west-2")

# Start a code interpreter session
client.start()
print(f"Code interpreter session started")

try:
    # Use the code interpreter
    result = client.invoke("listFiles")
    for event in result["stream"]:
        print(event["result"]["content"])

finally:
    # Always close the session when done
    client.stop()
```

## Execute Code

Use the `invoke` method to execute code in your session:

```
from bedrock_agentcore.tools.code_interpreter_client import code_session

with code_session("us-west-2") as client:
    # Execute Python code
    code_to_execute = """
import matplotlib.pyplot as plt
import numpy as np

# Generate data
x = np.linspace(0, 10, 100)
y = np.sin(x)

# Create plot
plt.figure(figsize=(10, 6))
plt.plot(x, y, 'b-', linewidth=2)
plt.title('Sine Wave')
plt.xlabel('x')
plt.ylabel('sin(x)')
plt.grid(True)
plt.show()

print("Code execution completed successfully!")
"""

    # Execute the code
    result = client.invoke("executeCode", {"language": "python", "code": code_to_execute})

    # Process the streaming results
    for event in result["stream"]:
        print(event["result"]["content"])
```

## Integrating with Agents

You can integrate the Code Interpreter with your agents to enable code execution capabilities:

```
import json
from strands import Agent, tool
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter

# Global code interpreter client
code_client = CodeInterpreter("us-west-2")

# Validation-focused system prompt
SYSTEM_PROMPT = """You are an AI assistant that validates answers through code execution.
When asked about code, algorithms, or calculations, write Python code to verify your answers."""


@tool
def execute_python(code: str) -> str:
    """Execute Python code in the code interpreter."""

    # Show the code being executed
    print("\nExecuting Python code:")
    print(code)

    # Execute the code
    response = code_client.invoke("executeCode", {"language": "python", "code": code})

    # Process the streaming results
    output = []

    for event in response["stream"]:
        if "result" in event and "content" in event["result"]:
            content = event["result"]["content"]
            output.append(content)
            print(content)

    return json.dumps(output[-1])


def demo():
    """Main function demonstrating the code interpreter agent"""
    try:
        code_client.start()

        # Create the agent with the execute_python tool
        agent = Agent(
            tools=[execute_python],
            system_prompt=SYSTEM_PROMPT,
        )

        prompt = "Calculate the first 10 Fibonacci numbers."
        print(f"\nPrompt: {prompt}\n")

        response = agent(prompt)
        # Print the response
        print("\nAgent Response:")
        print(response.message)
    finally:
        code_client.stop()


if __name__ == "__main__":
    demo()
```

## Best Practices

To get the most out of the Code Interpreter:

1. **Use context managers**: The `code_session` context manager ensures proper cleanup
1. **Handle errors gracefully**: Always include try/except blocks
1. **Process streaming results**: Code execution results are returned as streams
1. **Manage files properly**: Clean up temporary files when no longer needed
1. **Close sessions**: Always close sessions when done to release resources
