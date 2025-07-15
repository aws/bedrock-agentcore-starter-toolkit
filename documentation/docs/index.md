# Amazon Bedrock AgentCore

Amazon Bedrock AgentCore is a comprehensive platform for deploying and operating highly effective AI agents securely at scale. The platform includes a Python SDK and Starter Toolkit that work together to help you build, deploy, and manage agent applications.

[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/aws/bedrock-agentcore-sdk-python)](https://github.com/aws/bedrock-agentcore-sdk-python/graphs/commit-activity)
[![License](https://img.shields.io/github/license/aws/bedrock-agentcore-sdk-python)](https://github.com/aws/bedrock-agentcore-sdk-python/blob/main/LICENSE)
[![PyPI version](https://img.shields.io/pypi/v/bedrock-agentcore)](https://pypi.org/project/bedrock-agentcore)

<div style="display: flex; gap: 10px; margin: 20px 0;">
  <a href="https://github.com/aws/bedrock-agentcore-sdk-python" class="md-button">Python SDK</a>
  <a href="https://github.com/aws/bedrock-agentcore-starter-toolkit" class="md-button">Starter Toolkit</a>
  <a href="https://github.com/awslabs/amazon-bedrock-agentcore-samples" class="md-button">Samples</a>
</div>

!!! warning "Preview Status"
    Amazon Bedrock AgentCore is currently in preview release. APIs may change as we refine the platform.

## Transform Any Function Into a Production API in 3 Lines

Bedrock AgentCore allows you to transform your existing AI agent code into a production-ready HTTP API with just 3 lines of code:

```python
from bedrock_agentcore.runtime import BedrockAgentCoreApp  # +1
app = BedrockAgentCoreApp()                                # +2

@app.entrypoint                                           # +3
def invoke(payload):  # ← Your function stays EXACTLY the same
    user_message = payload.get("prompt", "Hello")
    response = agent(user_message)
    return response
```

Your function is now a production-ready API server with health monitoring, streaming support, and AWS integration.

## Platform Components

### 🔧 Bedrock AgentCore SDK

The SDK provides Python primitives for agent development with built-in support for:

- **Runtime**: Lightweight wrapper to convert functions into API servers
- **Memory**: Persistent storage for conversation history and agent context
- **Tools**: Built-in clients for code interpretation and browser automation
- **Identity**: Secure authentication and access management

### 🚀 Bedrock AgentCore Starter Toolkit

The Toolkit provides CLI tools and higher-level abstractions for:

- **Deployment**: Containerize and deploy agents to AWS infrastructure
- **Gateway Integration**: Transform existing APIs into agent tools
- **Configuration Management**: Manage environment and deployment settings
- **Observability**: Monitor agents in production environments

## Platform Services

Amazon Bedrock AgentCore provides enterprise-grade services for AI agent development:

- 🚀 **AgentCore Runtime** - Serverless deployment and scaling for dynamic AI agents
- 🧠 **AgentCore Memory** - Persistent knowledge with event and semantic memory
- 💻 **AgentCore Code Interpreter** - Secure code execution in isolated sandboxes
- 🌐 **AgentCore Browser** - Fast, secure cloud-based browser for web interaction
- 🔗 **AgentCore Gateway** - Transform existing APIs into agent tools
- 📊 **AgentCore Observability** - Real-time monitoring and tracing
- 🔐 **AgentCore Identity** - Secure authentication and access management

## Getting Started

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } __SDK Quickstart__

    ---

    Get started with the core SDK for agent development

    [:octicons-arrow-right-24: Start coding](user-guide/runtime/quickstart.md)

-   :material-tools:{ .lg .middle } __Toolkit Guide__

    ---

    Learn to deploy and manage agents in production

    [:octicons-arrow-right-24: Deploy agents](user-guide/runtime/overview.md)

-   :material-api:{ .lg .middle } __API Reference__

    ---

    Detailed API documentation for developers

    [:octicons-arrow-right-24: Explore APIs](api-reference/runtime.md)

</div>

## Features

- **Zero Code Changes**: Your existing functions remain untouched
- **Production Ready**: Automatic HTTP endpoints with health monitoring
- **Streaming Support**: Native support for generators and async generators
- **Framework Agnostic**: Works with any AI framework (Strands, LangGraph, LangChain, custom)
- **AWS Optimized**: Ready for deployment to AWS infrastructure
- **Enterprise Security**: Built-in identity, isolation, and access controls
