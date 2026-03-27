# Amazon Bedrock AgentCore

Amazon Bedrock AgentCore is a comprehensive platform for deploying and operating highly effective AI agents securely at scale. The platform includes a Python SDK and Starter Toolkit that work together to help you build, deploy, and manage agent applications.

[![GitHub commit activity](https://img.shields.io/github/commit-activity/m/aws/bedrock-agentcore-sdk-python)](https://github.com/aws/bedrock-agentcore-sdk-python/graphs/commit-activity)
[![License](https://img.shields.io/github/license/aws/bedrock-agentcore-sdk-python)](https://github.com/aws/bedrock-agentcore-sdk-python/blob/main/LICENSE)
[![PyPI version](https://img.shields.io/pypi/v/bedrock-agentcore)](https://pypi.org/project/bedrock-agentcore)

<div style="display: flex; gap: 10px; margin: 20px 0;">
  <a href="https://github.com/aws/agentcore-cli" class="md-button md-button--primary">AgentCore CLI (Recommended)</a>
  <a href="https://github.com/aws/bedrock-agentcore-sdk-python" class="md-button">Python SDK</a>
  <a href="https://github.com/aws/bedrock-agentcore-starter-toolkit" class="md-button">Starter Toolkit</a>
  <a href="https://github.com/awslabs/amazon-bedrock-agentcore-samples" class="md-button">Samples</a>
</div>

!!! tip "Recommendation: Use the AgentCore CLI for new projects"

    The **[AgentCore CLI (`@aws/agentcore-cli`)](https://github.com/aws/agentcore-cli)** is now the recommended way to create, develop, and deploy AI agents on Amazon Bedrock AgentCore. It offers broader framework support, local development with hot reload, built-in evaluations, gateway management, and more.

    **Get started:**
    ```bash
    npx @aws/agentcore-cli create
    ```

    **See the [AgentCore CLI docs](https://github.com/aws/agentcore-cli/tree/main/docs)** for the full commands reference, supported frameworks, configuration, and migration guidance.

    This starter toolkit remains available for existing Python-based workflows.

## 🚀 From Local Development to Bedrock AgentCore

```python
# Your existing agent (any framework)
from strands import Agent
# or LangGraph, CrewAI, Autogen, custom logic - doesn't matter

def my_local_agent(query):
    # Your carefully crafted agent logic
    return agent.process(query)

# Deploy to Bedrock AgentCore
from bedrock_agentcore import BedrockAgentCoreApp
app = BedrockAgentCoreApp()

@app.entrypoint
def production_agent(request):
    return my_local_agent(request['query'])  # Same logic, enterprise platform

production_agent.run()  # Ready to run on Bedrock AgentCore
```

**What you get with Bedrock AgentCore:**


- ✅ **Keep your agent logic** - Works with Strands, LangGraph, CrewAI, Autogen, custom frameworks.
- ✅ **Zero infrastructure management** - No servers, containers, or scaling concerns.
- ✅ **Enterprise-grade platform** - Built-in auth, memory, observability, security.
- ✅ **Production-ready deployment** - Reliable, scalable, compliant hosting.

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

- **Deployment**: Deploy Python agents directly to AWS infrastructure (direct_code_deploy) or containerize for complex scenarios
- **Import Agent**: Migrate existing Bedrock Agents to AgentCore with framework conversion
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

-   :material-import:{ .lg .middle } __Import Agent__

    ---

    Migrate existing Bedrock Agents to AgentCore

    [:octicons-arrow-right-24: Import agents](user-guide/import-agent/overview.md)

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
