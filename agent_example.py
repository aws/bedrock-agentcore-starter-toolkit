from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

app = BedrockAgentCoreApp()
agent = Agent()


@app.entrypoint
def agent_invocation(payload):
    """Handler for agent invocation"""
    user_message = payload.get(
        "prompt", "No prompt found in input, please guide customer to create a json payload with prompt key"
    )
    app.logger.info("invoking agent with user message: %s", payload)
    response = agent(user_message)
    app.logger.info("response payload: %s", response)
    return response
    # return "hello"


app.run()
