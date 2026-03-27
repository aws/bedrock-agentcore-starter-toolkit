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

> **⚠️ Recommendation: Use the AgentCore CLI for new projects**
>
> The **[AgentCore CLI (`@aws/agentcore-cli`)](https://github.com/aws/agentcore-cli)** is now the recommended way to create, develop, and deploy AI agents on Amazon Bedrock AgentCore. It supports a broader set of frameworks (Strands, LangGraph, LangChain, Google ADK, OpenAI Agents, and BYO), provides local development with hot reload, built-in evaluations, gateway management, and more.
>
> **For new projects**, install the AgentCore CLI:
> ```bash
> npm i @aws/agentcore-cli
> ```
>
> **Migrating from this toolkit?** See the [AgentCore CLI documentation](https://github.com/aws/agentcore-cli/tree/main/docs) for:
> - [Commands reference](https://github.com/aws/agentcore-cli/blob/main/docs/commands.md) — create, deploy, dev, invoke, add, remove, logs, traces, evals
> - [Supported frameworks](https://github.com/aws/agentcore-cli/blob/main/docs/frameworks.md) — Strands, LangGraph, LangChain, Google ADK, OpenAI Agents, BYO, and import from existing projects
> - [Configuration guide](https://github.com/aws/agentcore-cli/blob/main/docs/configuration.md) — agentcore.json, mcp.json, environment setup
> - [Local development](https://github.com/aws/agentcore-cli/blob/main/docs/local-development.md) — hot reload dev server
> - [Memory](https://github.com/aws/agentcore-cli/blob/main/docs/memory.md), [Gateway](https://github.com/aws/agentcore-cli/blob/main/docs/gateway.md), [Evaluations](https://github.com/aws/agentcore-cli/blob/main/docs/evals.md)
> - [IAM permissions](https://github.com/aws/agentcore-cli/blob/main/docs/PERMISSIONS.md)
>
> This starter toolkit remains available for existing Python-based workflows but is no longer the recommended starting point.

## Overview
Amazon Bedrock AgentCore enables you to deploy and operate highly effective agents securely, at scale using any framework and model. With Amazon Bedrock AgentCore, developers can accelerate AI agents into production with the scale, reliability, and security, critical to real-world deployment. AgentCore provides tools and capabilities to make agents more effective and capable, purpose-built infrastructure to securely scale agents, and controls to operate trustworthy agents. Amazon Bedrock AgentCore services are composable and work with popular open-source frameworks and any model, so you don’t have to choose between open-source flexibility and enterprise-grade security and reliability.

Amazon Bedrock AgentCore includes the following modular Services that you can use together or independently:

## 🚀 Jump Into AgentCore

> **New projects should use the [AgentCore CLI](https://github.com/aws/agentcore-cli):** `npm i @aws/agentcore-cli`

If you prefer a Python-based workflow, you can still get started with this toolkit using `agentcore create`.

Pick your favorite Agent SDK framework and model provider like Strands with Amazon Bedrock. You'll get a brand new project ready to be deployed onto AgentCore.

**[Create Quick Start (Starter Toolkit)](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/create/quickstart.html)** · **[Create Quick Start (AgentCore CLI)](https://github.com/aws/agentcore-cli/blob/main/docs/commands.md)**

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

### Recommended: AgentCore CLI

```bash
npm i @aws/agentcore-cli
```

See the [AgentCore CLI README](https://github.com/aws/agentcore-cli) and [docs](https://github.com/aws/agentcore-cli/tree/main/docs) for full usage.

### Starter Toolkit (Python)

If you prefer a Python-based workflow:

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


## 📝 License & Contributing

- **License:** Apache 2.0 - see [LICENSE.txt](LICENSE.txt)
- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security:** Report vulnerabilities via [SECURITY.md](SECURITY.md)
