# Amazon Bedrock AgentCore SDK

The Bedrock AgentCore SDK is your gateway to Amazon Bedrock AgentCore—a comprehensive platform for deploying and operating highly effective AI agents securely at scale. The SDK provides Python primitives for agent development with built-in support for memory management, identity handling, and various tools.

## About Amazon Bedrock AgentCore

Amazon Bedrock AgentCore enables you to deploy and operate highly effective agents securely, at scale using any framework and model. With AgentCore, developers can accelerate AI agents into production with enterprise-grade scale, reliability, and security. The platform provides:

- **Composable Services**: Mix and match services to fit your needs
- **Framework Flexibility**: Works with LangGraph, CrewAI, Strands, and more
- **Any Model Support**: Not locked into specific models
- **Enterprise Security**: Built-in identity, isolation, and access controls

!!! warning "Preview"

    Amazon Bedrock AgentCore SDK is currently in preview release. APIs may change as we refine the platform and SDK.

## Platform Services Integration

The SDK provides seamless access to Amazon Bedrock AgentCore services:

🚀 **AgentCore Runtime** - Serverless deployment and scaling for dynamic AI agents with fast cold starts and framework flexibility.
🧠 **AgentCore Memory** - Persistent knowledge with event and semantic memory for cross-session continuity.
💻 **AgentCore Code Interpreter** - Secure code execution in isolated sandbox environments with multi-language support.
🌐 **AgentCore Browser** -  Fast, secure cloud-based browser for automated web interaction at enterprise scale.
🔗 **AgentCore Gateway** - Transform existing APIs and Lambda functions into fully-managed MCP tools.
📊 **AgentCore Observability** - Real-time monitoring and tracing with OpenTelemetry support for production insights.
🔐 **AgentCore Identity** - Secure authentication and access management for AWS services and third-party integrations.

## Key Features

### 🚀 **Agent Runtime & Deployment**
- **Lightweight wrapper**: Convert any Python function into an AgentCore-compatible agent
- **Serverless runtime**: Runs on AgentCore Runtime with industry-leading performance
- **HTTP server handling**: Automatic `/invocations` and `/ping` endpoints
- **Local testing**: Test agents locally before deploying to AWS

### 🧠 **Advanced Memory Management**
- **Persistent memory**: Powered by AgentCore Memory for cross-session knowledge
- **Event & semantic memory**: Store raw interactions and extracted insights
- **Conversation branching**: Create and manage conversation branches for A/B testing
- **Flexible strategies**: Multiple memory approaches and namespaces

### 🛠 **Built-in Tools**
- **Browser integration**: Powered by AgentCore Browser for automated web browsing
- **Code interpreter**: Secure code execution via AgentCore Code Interpreter in isolated sandboxes

### 🔗 **Gateway Tools**
- **API integration**: Transform existing REST APIs into MCP-compatible tools
- **Lambda functions**: Connect Lambda functions as agent tools with defined schemas
- **Authentication management**: OAuth and credential lifecycle for external services
- **Standardized interface**: Unified MCP protocol for diverse tool integration

### 📊 **Observability & Monitoring**
- **Real-time insights**: Monitor agent performance, token usage, and operational metrics
- **OpenTelemetry support**: Industry-standard telemetry for comprehensive tracing
- **CloudWatch integration**: Seamless logging and metrics through AgentCore Observability
- **Debug capabilities**: Detailed visibility into agent workflow and behavior
- **Production monitoring**: Error tracking, latency metrics, and session analytics

### 🔐 **Identity & Authentication**
- **Secure by default**: Built on AgentCore Identity service
- **AWS integration**: Built-in support for AWS authentication
- **Token management**: Automatic token polling and refresh
- **Enterprise-grade security**: Identity isolation and access controls

## Getting Started

### Are you a first-time Amazon Bedrock AgentCore user?

If you are new to Amazon Bedrock AgentCore, we recommend starting with these guides:

1. **[Host agents with AgentCore Runtime](user-guide/runtime/quickstart.md)** - Deploy your first agent
2. **[Add memory to your AI agent](user-guide/memory/quickstart.md)** - Enable persistent conversations
4. **[Connect tools with AgentCore Gateway](examples/gateway-integration.md)** - Integrate external APIs

### Code Examples

For comprehensive code examples and sample implementations, see our [GitHub samples repository](https://github.com/awslabs/amazon-bedrock-agentcore-samples/).
