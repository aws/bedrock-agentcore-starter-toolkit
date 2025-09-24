import os
from dotenv import load_dotenv
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

# Load environment variables
load_dotenv()

app = BedrockAgentCoreApp()
agent = Agent(
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region=os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
)


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

if __name__ == "__main__":
    # Test locally before running the server
    test_payload = {"prompt": "Hello, how are you?"}
    result = agent_invocation(test_payload)
    print(f"Test result: {result}")
    
    # Uncomment to run the server
    # app.run()
