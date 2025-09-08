<div align="center">
  <h1>
    Bedrock AgentCore Starter Toolkit
  </h1>

  <h2>
    Deploy your local AI agent to Bedrock AgentCore with zero infrastructure
  </h2>

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

## Overview
Amazon Bedrock AgentCore enables you to deploy and operate highly effective agents securely, at scale using any framework and model. With Amazon Bedrock AgentCore, developers can accelerate AI agents into production with the scale, reliability, and security, critical to real-world deployment. AgentCore provides tools and capabilities to make agents more effective and capable, purpose-built infrastructure to securely scale agents, and controls to operate trustworthy agents. Amazon Bedrock AgentCore services are composable and work with popular open-source frameworks and any model, so you don’t have to choose between open-source flexibility and enterprise-grade security and reliability.

Amazon Bedrock AgentCore includes the following modular Services that you can use together or independently:

## 🚀 Amazon Bedrock AgentCore Runtime
AgentCore Runtime is a secure, serverless runtime purpose-built for deploying and scaling dynamic AI agents and tools using any open-source framework including LangGraph, CrewAI, and Strands Agents, any protocol, and any model. Runtime was built to work for agentic workloads with industry-leading extended runtime support, fast cold starts, true session isolation, built-in identity, and support for multi-modal payloads. Developers can focus on innovation while Amazon Bedrock AgentCore Runtime handles infrastructure and security -- accelerating time-to-market

**[Runtime Quick Start](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/quickstart.html)**

## 🧠 Amazon Bedrock AgentCore Memory
AgentCore Memory makes it easy for developers to build context aware agents by eliminating complex memory infrastructure management while providing full control over what the AI agent remembers. Memory provides industry-leading accuracy along with support for both short-term memory for multi-turn conversations and long-term memory that can be shared across agents and sessions.


**[Memory Quick Start](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/memory/quickstart.html)**

## 🔗 Amazon Bedrock AgentCore Gateway
Amazon Bedrock AgentCore Gateway acts as a managed Model Context Protocol (MCP) server that converts APIs and Lambda functions into MCP tools that agents can use. Gateway manages the complexity of OAuth ingress authorization and secure egress credential exchange, making standing up remote MCP servers easier and more secure. Gateway also offers composition and built-in semantic search over tools, enabling developers to scale their agents to use hundreds or thousands of tools.

**[Gateway Quick Start](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/gateway/quickstart.html)**

## 💻 Amazon Bedrock AgentCore Code Interpreter
AgentCore Code Interpreter tool enables agents to securely execute code in isolated sandbox environments. It offers advanced configuration support and seamless integration with popular frameworks. Developers can build powerful agents for complex workflows and data analysis while meeting enterprise security requirements.

**[Code Interpreter Quick Start](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/builtin-tools/quickstart-code-interpreter.html)**

## 🌐 Amazon Bedrock AgentCore Browser
AgentCore Browser tool provides a fast, secure, cloud-based browser runtime to enable AI agents to interact with websites at scale. It provides enterprise-grade security, comprehensive observability features, and automatically scales— all without infrastructure management overhead.

**[Browser Quick Start](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/builtin-tools/quickstart-browser.html)**

## 📊 Amazon Bedrock AgentCore Observability
AgentCore Observability helps developers trace, debug, and monitor agent performance in production through unified operational dashboards. With support for OpenTelemetry compatible telemetry and detailed visualizations of each step of the agent workflow, AgentCore enables developers to easily gain visibility into agent behavior and maintain quality standards at scale.

**[Observability Quick Start](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/observability/quickstart.html)**

## 🔐 Amazon Bedrock AgentCore Identity
AgentCore Identity provides a secure, scalable agent identity and access management capability accelerating AI agent development. It is compatible with existing identity providers, eliminating needs for user migration or rebuilding authentication flows. AgentCore Identity's helps to minimize consent fatigue with a secure token vault and allows you to build streamlined AI agent experiences. Just-enough access and secure permission delegation allow agents to securely access AWS resources and third-party tools and services.

**[Identity Quick Start](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/identity/quickstart.html)**

## 🔐 Import Amazon Bedrock Agents to Bedrock AgentCore
AgentCore Import-Agent enables seamless migration of existing Amazon Bedrock Agents to LangChain/LangGraph or Strands frameworks while automatically integrating AgentCore primitives like Memory, Code Interpreter, and Gateway. Developers can migrate agents in minutes with full feature parity and deploy directly to AgentCore Runtime for serverless operation.

**[Import Agent Quick Start](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/import-agent/quickstart.html)**


## ⚠️ Preview Status

Bedrock AgentCore is currently in public preview.

## 📝 License & Contributing

- **License:** Apache 2.0 - see [LICENSE.txt](LICENSE.txt)
- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security:** Report vulnerabilities via [SECURITY.md](SECURITY.md)
