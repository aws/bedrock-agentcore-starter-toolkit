# Import Agent Overview

The `import-agent` utility enables you to migrate existing Amazon Bedrock Agents to Bedrock AgentCore, converting them into framework-specific implementations while leveraging AgentCore's enterprise-grade primitives.

> **Note** Use the output agent definition as a starting point for your custom agent implementation. Review the generated code, evaluate agent behavior, and make necessary changes before deploying. Extend the agent with additional tools, memory, and other features as required.
>
> **Note** Use the output agent definition as a starting point for your custom agent implementation. Review the generated code, evaluate agent behavior, and make necessary changes before deploying. Extend the agent with additional tools, memory, and other features as required.

## What is Import Agent?

The import-agent utility automates the process of:

1. **Fetching** your existing Bedrock Agent configuration
1. **Converting** it to LangChain/LangGraph or Strands framework code
1. **Integrating** AgentCore primitives (Memory, Code Interpreter, Observability, Gateway)
1. **Integrating** AgentCore primitives (Memory, Code Interpreter, Observability, Gateway)
1. **Deploying** to AgentCore Runtime (optional)

## Key Benefits

- **Framework Flexibility**: Convert to LangChain/LangGraph or Strands
- **Zero Infrastructure**: Leverage AgentCore's serverless platform
- **Enhanced Capabilities**: Add Memory, Code Interpreter, and Observability
- **Production Ready**: Deploy directly to AgentCore Runtime
- **Preserved Logic**: Maintains your agent's core functionality

## Supported Target Platforms

### LangChain + LangGraph

Perfect for teams already using the LangChain ecosystem or those looking for extensive third-party integrations.

### Strands

Ideal for teams wanting AWS-native agent development with streamlined patterns.

## Generated Output

The utility generates an agent implementation including:

- **Agent Code**: Framework-specific implementation of your Bedrock Agent
- **Dependencies**: All required packages and versions
- **Configuration**: Environment setup and deployment configuration
- **AgentCore Integration**: Memory, Code Interpreter, and Observability primitives

## Migration Workflow

```
flowchart TD
    A[Existing Bedrock Agent] --> B[Import Agent Utility]
    B --> C{Select Target Platform}
    C --> D[LangChain/LangGraph]
    C --> E[Strands]
    D --> F[Generate Agent Code]
    E --> F
    F --> G{Deploy to Runtime?}
    G -->|Yes| H[AgentCore Runtime]
    G -->|No| I[Local Development]
```

## Feature Support

| Bedrock Agent Feature                            | Langchain | Strands   | AgentCore                          |
| ------------------------------------------------ | --------- | --------- | ---------------------------------- |
| *Guardrails*                                     | SUPPORTED | SUPPORTED |                                    |
| *Orchestration (via reAct)*                      | SUPPORTED | SUPPORTED |                                    |
| *Knowledge Bases*                                | SUPPORTED | SUPPORTED |                                    |
| *Code Interpreter*                               | SUPPORTED | SUPPORTED | SUPPORTED: 1P Code Interpreter     |
| *Lambda Function Definitions*                    | SUPPORTED | SUPPORTED | SUPPORTED: AgentCore Gateway       |
| *Lambda OpenAPI Definitions*                     | SUPPORTED | SUPPORTED | SUPPORTED: AgentCore Gateway       |
| *Return of Control*                              | SUPPORTED | SUPPORTED |                                    |
| *Short Term (Conversational) Memory*             | SUPPORTED | SUPPORTED |                                    |
| *Long Term (Cross-Session) Memory*               | SUPPORTED | SUPPORTED | SUPPORTED: AgentCore Memory        |
| *Session Summarization*                          | SUPPORTED | SUPPORTED | SUPPORTED: AgentCore Memory        |
| *Pre Processing Step*                            | SUPPORTED | SUPPORTED |                                    |
| *Post Processing Step*                           | SUPPORTED | SUPPORTED |                                    |
| *KB Generation Routing/Optimizations*            | SUPPORTED | SUPPORTED |                                    |
| *Idle Timeouts*                                  | SUPPORTED | SUPPORTED |                                    |
| *User Input (as a tool)*                         | SUPPORTED | SUPPORTED |                                    |
| *Traces*                                         | SUPPORTED | SUPPORTED | SUPPORTED: AgentCore Observability |
| *Multi-Agent Collaboration - Supervisor Mode*    | SUPPORTED | SUPPORTED |                                    |
| *Multi-Agent Collaboration - Routing Mode*       | SUPPORTED | SUPPORTED |                                    |
| *Multi-Agent Collaboration - Conversation Relay* | SUPPORTED | SUPPORTED |                                    |
| *Custom Bedrock Model Usage*                     | SUPPORTED | SUPPORTED |                                    |
| *Chat Interface (via CLI)*                       | SUPPORTED | SUPPORTED |                                    |
| *Custom Inference Configurations*                | SUPPORTED | SUPPORTED |                                    |
| *Agent Deployment*                               | N/A       | N/A       | SUPPORTED: AgentCore Runtime       |
| *Lambda Parsing and Orchestration*               | N/A       | N/A       |                                    |

## Next Steps

- [Quick Start Guide](quickstart.html) - Get started in 5 minutes
- [Configuration Reference](configuration.html) - Detailed parameter guide
- [Design Choices](design.html) - Details on the design of the generated agent
- [Design Choices](design.html) - Details on the design of the generated agent
