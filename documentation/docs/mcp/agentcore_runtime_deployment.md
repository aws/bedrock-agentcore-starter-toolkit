### Build your first agent or transform existing code

#### Prerequisites & Environment Setup
- **Environment**: Set up Python 3.10+ and virtual environment - [Environment Setup](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/quickstart.html#step-0-setup-folder-and-virtual-environment)

#### Step 1: Install Dependencies & Create Agent Code
- **New Agents**: Install AgentCore packages and create your agent using hello world strands agents  [Installation & Creation Guide](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/quickstart.html#step-1-install-and-create-your-agent)
- **Existing Agents**: Transform your current agent code to work with AgentCore - [Framework Integration Examples](https://aws.github.io/bedrock-agentcore-starter-toolkit/examples/index.html)

#### Step 1.1: For strands refer to following documentation
- [Welcome](https://strandsagents.com/latest/documentation/docs/index.md)
- [Amazon Bedrock](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/model-providers/amazon-bedrock/index.md)
- [Amazon Bedrock AgentCore](https://strandsagents.com/latest/documentation/docs/user-guide/deploy/deploy_to_bedrock_agentcore/index.md)
1. Import strands agent - `from strands import Agent`
2. Create an agent with default settings - agent = Agent()
3. Ask the agent a question - agent("Tell me about agentic AI")

#### Step 1.2 - Transforming agent code for agentcore
- **Agent code**: Always use these [code patterns](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/overview.html#agent-development-patterns) for agent code.
- **AgentCore Wrapper**: Use  [bedrock-agentcore](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/overview.html#what-is-the-agentcore-runtime-sdk) wrappers to implement runtime service contract.
1. Import the Runtime App with from bedrock_agentcore.runtime import BedrockAgentCoreApp
2. Initialize the App in your code with app = BedrockAgentCoreApp()
3. Decorate the invocation function with the @app.entrypoint decorator
4. Create a requirements.txt file with needed packages. Note: if strands-tools is detected, the correct library to add is strands-agents-tools
5. Let AgentCore Runtime control the running of the agent with app.run()

#### Step 2: Local Development & Testing (Optional)
- **Local Testing**: Run and test your agent locally before deployment - [Local Testing Guide](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/quickstart.html#step-2-test-locally)
1. Start the agent using python <my_agent.py>
2. # Test it (in another terminal)
    curl -X POST http://localhost:8080/invocations \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Hello!"}'
3. Stop the agent.

#### Step 3: Deploy to AgentCore using CLI
Refer to https://aws.github.io/bedrock-agentcore-starter-toolkit/api-reference/cli.html
1. Install cli with 'pip install bedrock-agentcore-starter-toolkit'
2. **Configuration**: Use AgentCore CLI to configure your agent for deployment.
    ```agentcore configure --entrypoint converted_agentcore_file.py --non-interactive```
3. **Deployment**: Launch your agent to AWS with automatic resource creation.
    ```agentcore launch```
4. **Invocation**: agentcore invoke '{"prompt": "Hello"}' Test your deployed agent using the CLI or API calls

#### Step 4: Troubleshooting & Enhancement
- **Common Issues**: Resolve deployment and runtime issues - [Troubleshooting Guide](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/quickstart.html#troubleshooting)
- **Advanced Features**: Add memory, authentication, and gateway integrations - [Next Steps](https://aws.github.io/bedrock-agentcore-starter-toolkit/user-guide/runtime/quickstart.html#next-steps)
- **Monitoring**: Set up observability and monitoring for production agents
