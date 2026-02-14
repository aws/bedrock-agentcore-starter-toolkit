<div align="center">
  <h1>
    Bedrock AgentCore Starter Toolkit
  </h1>

  <div align="center">
    <a href="https://github.com/aws/bedrock-agentcore-starter-toolkit/graphs/commit-activity"><img alt="GitHub commit activity" src="https://img.shields.io/github/commit-activity/m/aws/bedrock-agentcore-starter-toolkit"/></a>
    <a href="https://github.com/aws/bedrock-agentcore-starter-toolkit/issues"><img alt="GitHub open issues" src="https://img.shields.io/github/issues/aws/bedrock-agentcore-starter-toolkit"/></a>
    <a href="https://github.com/aws/bedrock-agentcore-starter-toolkit/pulls"><img alt="GitHub open pull requests" src="https://img.shields.io/github/issues-pr/aws/bedrock-agentcore-starter-toolkit"/></a>
    <a href="https://github.com/aws/bedrock-agentcore-starter-toolkit/blob/main/LICENSE.txt"><img alt="License" src="https://img.shields.io/github/license/aws/bedrock-agentcore-starter-toolkit"/></a>
    <a href="https://pypi.org/project/bedrock-agentcore-starter-toolkit"><img alt="PyPI version" src="https://img.shields.io/pypi/v/bedrock-agentcore-starter-toolkit"/></a>
    <a href="https://python.org"><img alt="Python versions" src="https://img.shields.io/pypi/pyversions/bedrock-agentcore-starter-toolkit"/></a>
  </div>

  <p>
  <a href="https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/what-is-bedrock-agentcore.html">Documentation</a>
    ◆ <a href="https://github.com/awslabs/amazon-bedrock-agentcore-samples">Samples</a>
    ◆ <a href="https://discord.gg/bedrockagentcore-preview">Discord</a>
    ◆ <a href="https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/bedrock-agentcore-control.html">Boto3 Python SDK</a>
    ◆ <a href="https://github.com/aws/bedrock-agentcore-sdk-python">Runtime Python SDK</a>
    ◆ <a href="https://github.com/aws/bedrock-agentcore-starter-toolkit">Starter Toolkit</a>

  </p>
</div>

<br/>
<b>Note: The AgentCore Starter Toolkit is an experimental offering and features are subject to change in future releases.</b>

## Overview

Amazon Bedrock AgentCore enables you to deploy and operate highly effective agents securely, at scale using any framework and model. With Amazon Bedrock AgentCore, developers can accelerate AI agents into production with the scale, reliability, and security, critical to real-world deployment. AgentCore provides tools and capabilities to make agents more effective and capable, purpose-built infrastructure to securely scale agents, and controls to operate trustworthy agents. Amazon Bedrock AgentCore services are composable and work with popular open-source frameworks and any model, so you don’t have to choose between open-source flexibility and enterprise-grade security and reliability.

Amazon Bedrock AgentCore includes the following modular Services that you can use together or independently:

## 🚀 Jump Into AgentCore
Get started quickly with `agentcore create`.

Pick your favorite Agent SDK framework and model provider like Strands with Amazon Bedrock. You'll get a brand new project ready to be deployed onto AgentCore.

**[Create Quick Start](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/create/quickstart.html)**

## 🛠️ Amazon Bedrock AgentCore Runtime
AgentCore Runtime is a secure, serverless runtime purpose-built for deploying and scaling dynamic AI agents and tools using any open-source framework including LangGraph, CrewAI, and Strands Agents, any protocol, and any model. Runtime was built to work for agentic workloads with industry-leading extended runtime support, fast cold starts, true session isolation, built-in identity, and support for multi-modal payloads. Developers can focus on innovation while Amazon Bedrock AgentCore Runtime handles infrastructure and security -- accelerating time-to-market

**[Runtime Quick Start](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-toolkit.html)**

## 🧠 Amazon Bedrock AgentCore Memory

AgentCore Memory makes it easy for developers to build context aware agents by eliminating complex memory infrastructure management while providing full control over what the AI agent remembers. Memory provides industry-leading accuracy along with support for both short-term memory for multi-turn conversations and long-term memory that can be shared across agents and sessions.

**[Memory Quick Start](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/memory-get-started.html)**

## 🔗 Amazon Bedrock AgentCore Gateway

Amazon Bedrock AgentCore Gateway acts as a managed Model Context Protocol (MCP) server that converts APIs and Lambda functions into MCP tools that agents can use. Gateway manages the complexity of OAuth ingress authorization and secure egress credential exchange, making standing up remote MCP servers easier and more secure. Gateway also offers composition and built-in semantic search over tools, enabling developers to scale their agents to use hundreds or thousands of tools.

**[Gateway Quick Start](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-quick-start.html)**

## 💻 Amazon Bedrock AgentCore Code Interpreter

AgentCore Code Interpreter tool enables agents to securely execute code in isolated sandbox environments. It offers advanced configuration support and seamless integration with popular frameworks. Developers can build powerful agents for complex workflows and data analysis while meeting enterprise security requirements.

**[Code Interpreter Quick Start](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-getting-started.html)**

## 🌐 Amazon Bedrock AgentCore Browser

AgentCore Browser tool provides a fast, secure, cloud-based browser runtime to enable AI agents to interact with websites at scale. It provides enterprise-grade security, comprehensive observability features, and automatically scales— all without infrastructure management overhead.

**[Browser Quick Start](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/browser-onboarding.html)**

## 📊 Amazon Bedrock AgentCore Observability

AgentCore Observability helps developers trace, debug, and monitor agent performance in production through unified operational dashboards. With support for OpenTelemetry compatible telemetry and detailed visualizations of each step of the agent workflow, AgentCore enables developers to easily gain visibility into agent behavior and maintain quality standards at scale.

**[Observability Quick Start](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-get-started.html)**

## 🎯 Amazon Bedrock AgentCore Evaluation
AgentCore Evaluation enables developers to assess and improve agent quality through built-in and custom evaluators. With support for on-demand evaluation and continuous monitoring via online evaluation, developers can measure agent performance metrics like helpfulness, correctness, and goal success rates. Evaluation integrates seamlessly with observability to provide actionable insights for maintaining and improving agent quality at scale.

**[Evaluation Documentation](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/evaluations.html)** • **[Quick Start](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/evaluation/quickstart.html)**

## 🔐 Amazon Bedrock AgentCore Identity

AgentCore Identity provides a secure, scalable agent identity and access management capability accelerating AI agent development. It is compatible with existing identity providers, eliminating needs for user migration or rebuilding authentication flows. AgentCore Identity's helps to minimize consent fatigue with a secure token vault and allows you to build streamlined AI agent experiences. Just-enough access and secure permission delegation allow agents to securely access AWS resources and third-party tools and services.

**[Identity Quick Start](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity-getting-started-cognito.html)**

## 🛡️ Amazon Bedrock AgentCore Policy
Policy in AgentCore gives you real time, deterministic control over agent's actions through AgentCore Gateway, ensuring agents stay within defined boundaries and business rules without slowing them down. Easily express fine-grained rules using natural language description or author them directly using Cedar - AWS's open-source policy language - giving you complete control over who can perform which actions under what conditions.

**[Policy Quick Start](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy-getting-started.html)**

## 🔐 Import Amazon Bedrock Agents to Bedrock AgentCore

AgentCore Import-Agent enables seamless migration of existing Amazon Bedrock Agents to LangChain/LangGraph or Strands frameworks while automatically integrating AgentCore primitives like Memory, Code Interpreter, and Gateway. Developers can migrate agents in minutes with full feature parity and deploy directly to AgentCore Runtime for serverless operation.

**[Import Agent Quick Start](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/import-agent/quickstart.html)**

## Installation

### Quick Start

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create the virtual environment (requires python 3.10) and activate it
uv venv --python 3.10
source .venv/bin/activate

# Install using uv (recommended)
uv pip install bedrock-agentcore-starter-toolkit

# Or alternatively with pip
pip install bedrock-agentcore-starter-toolkit

```

## 🖥️ Web UI for AgentCore

The Bedrock AgentCore Starter Toolkit includes a modern web interface for interacting with your agents and inspecting memory resources. The UI provides an intuitive chat interface and memory viewer, making it easy to test and demonstrate agent capabilities.

### Agent Requirements for UI Compatibility

For your AgentCore agent to work with the UI, it must accept input in the following format:

**Required Input Format:**

```json
{
  "prompt": "Your message here"
}
```

The UI sends user messages as a JSON payload with a `prompt` field containing the user's text. Your agent's entrypoint function should extract this field to process the message.

**Example Agent Implementation:**

```python
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

app = BedrockAgentCoreApp()
agent = Agent()

@app.entrypoint
def invoke(payload):
    """Agent entrypoint that accepts UI input format"""
    # Extract the prompt from the payload
    user_message = payload.get("prompt", "")

    # Process the message with your agent
    result = agent(user_message)

    # Return the response
    return {"result": result.message}
```

**Key Points:**

- The UI sends messages as `{"prompt": "user message"}`
- Your agent should read from `payload.get("prompt")` or `payload["prompt"]`
- Your agent can return any JSON-serializable response
- The UI will display the response content in the chat interface
- This format is compatible with the standard AgentCore Runtime invocation pattern

**Testing Compatibility:**

You can test your agent's compatibility with the UI format locally:

```bash
# Start your agent locally
python my_agent.py

# Test with the UI format
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!"}'
```

If your agent responds successfully, it will work with the UI.

### Launching the UI

Launch your agent with the `--ui` flag to automatically start the web interface:

```bash
# Launch with local agent (running in container)
agentcore launch --local --ui

# Launch with remote agent (deployed to AWS)
agentcore launch --ui

# Launch UI only connecting to remote agent (deployed to AWS)
agentcore ui
```

The UI will automatically open in your default browser at `http://localhost:8001`.

### Local vs Remote Mode

**Local Mode** (`--local` flag):

- Connects to an agent running locally in a Docker container at `http://127.0.0.1:8000`
- No AWS credentials required
- Perfect for development and testing
- No authentication needed

**Remote Mode** (default):

- Connects to an agent deployed to AWS via AgentCore Runtime
- Uses your AWS credentials from the environment (AWS CLI, environment variables, etc.)
- Supports IAM and OAuth authentication
- Reads agent configuration from `.bedrock_agentcore.yaml`

### Features

- **Interactive Chat**: Send messages to your agent and view responses in a clean chat interface
- **Session Management**: Create new conversation sessions to maintain context
- **Memory Inspector**: View memory resources, strategies, and configurations
- **Configuration Display**: See current agent settings, connection mode, and authentication method
- **Markdown Support**: Agent responses support formatted text, code blocks, and markdown

### UI Screenshots

The AgentCore UI provides:

- A responsive chat interface with user and agent message bubbles
- Real-time loading indicators during agent invocation
- A dedicated memory view showing all configured strategies
- Session ID display and new conversation controls
- Error handling with user-friendly messages

For more details on using the UI, see the [UI User Guide](src/bedrock_agentcore_starter_toolkit/ui/README.md).

## 📝 License & Contributing

- **License:** Apache 2.0 - see [LICENSE.txt](LICENSE.txt)
- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security:** Report vulnerabilities via [SECURITY.md](SECURITY.md)
