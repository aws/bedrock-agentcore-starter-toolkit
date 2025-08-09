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
    <a href="https://github.com/aws/bedrock-agentcore-sdk-python">Python SDK</a>
    ◆ <a href="https://github.com/aws/bedrock-agentcore-starter-toolkit">Starter Toolkit</a>
    ◆ <a href="https://github.com/awslabs/amazon-bedrock-agentcore-samples">Samples</a>
    ◆ <a href="https://discord.gg/bedrockagentcore-preview">Discord</a>
  </p>
</div>

## 🚀 From Local Development to Bedrock AgentCore

```python
# Build your agent with the SDK
from bedrock_agentcore import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
def my_agent(request):
    # Your existing Strands, LangGraph, CrewAI, or custom agent logic
    return process_with_your_framework(request.get("prompt"))

app.run()
```

```bash
# Deploy with the Starter Toolkit
agentcore configure --entrypoint my_agent.py
agentcore launch  # Ready to run on Bedrock AgentCore
agentcore invoke '{"prompt": "tell me a fact"}'
agentcore destroy
```

**What you get with the Starter Toolkit:**

- ✅ **Keep your agent logic** - Works with any SDK-built agent
- ✅ **Zero infrastructure management** - No servers, containers, or scaling concerns
- ✅ **One-command deployment** - From local development to enterprise platform
- ✅ **Production-ready hosting** - Reliable, scalable, compliant Bedrock AgentCore deployment

## ⚠️ Preview Status

Bedrock AgentCore Starter Toolkit is currently in public preview. APIs may change as we refine the SDK.

## 🛠️ Deployment & Management Tools

**Simple Configuration**

```bash
# Configure your agent for deployment
agentcore configure --entrypoint my_agent.py --name my-production-agent

# Check deployment status
agentcore status

# Invoke your deployed agent
agentcore invoke '{"prompt": "Hello from Bedrock AgentCore!"}'
```

**Enterprise Platform Services**

- 🚀 **Runtime** - Serverless deployment and scaling with fast cold starts
- 🧠 **Memory** - Persistent knowledge with event and semantic memory
- 🔗 **Gateway** - Transform existing APIs and Lambda functions into MCP tools
- 🔐 **Identity** - Secure authentication and access management
- 💻 **Code Interpreter** - Secure code execution in isolated sandbox environments
- 🌐 **Browser** - Fast, secure cloud-based browser for web automation
- 📊 **Observability** - Real-time monitoring and tracing with OpenTelemetry support

## ➡️ Importing from Bedrock Agents

Import from Bedrock Agents to AgentCore using the `import-agent` utility.

```bash
# Launch the import-agent workflow
agentcore import-agent
```

This will generate an equivalent Langchain or Strands agent in `./output`, leveraging AgentCore primitives, and provide an option to deploy the agent to AgentCore Runtime. See additional documentation on this utility:
- [Quickstart Guide](https://github.com/aws/bedrock-agentcore-starter-toolkit/blob/main/documentation/docs/user-guide/import-agent/quickstart.md)
- [Utility Overview](https://github.com/aws/bedrock-agentcore-starter-toolkit/blob/main/documentation/docs/user-guide/import-agent/overview.md)


## 📚 About Amazon Bedrock AgentCore

Amazon Bedrock AgentCore enables you to deploy and operate highly effective agents securely, at scale using any framework and model. With AgentCore, developers can accelerate AI agents into production with enterprise-grade scale, reliability, and security. The platform provides:

- **Composable Services**: Mix and match services to fit your needs
- **Framework Flexibility**: Works with Strands, LangGraph, CrewAI, Strands, and more
- **Any Model Support**: Not locked into specific models
- **Enterprise Security**: Built-in identity, isolation, and access controls

## 📝 License & Contributing

- **License:** Apache 2.0 - see [LICENSE.txt](LICENSE.txt)
- **Contributing:** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security:** Report vulnerabilities via [SECURITY.md](SECURITY.md)
