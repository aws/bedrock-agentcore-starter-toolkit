# AgentCore Code Interpreter Quickstart

AgentCore Code Interpreter enables your agents to execute Python code in a secure, managed environment. The agent can perform calculations, analyze data, generate visualizations, and validate answers through code execution.

## Prerequisites

Before you start, ensure you have:

* **AWS Account with credentials** configured. See instructions below.
* **Python 3.10+** installed
* [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html) installed
* **IAM Execution Role** with the required permissions (see below)
* **Model access**: Anthropic Claude Sonnet 4.0 [enabled](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html) in the Amazon Bedrock console. For information about using a different model with the Strands Agents see the *Model Providers* section in the [Strands Agents SDK](https://strandsagents.com/latest/documentation/docs/) documentation.
* **AWS Region** where AgentCore is available

### Credentials configuration (if not already configured)

**Verify your AWS Credentials**

Confirm your AWS credentials are configured:

```bash
aws sts get-caller-identity
```

If this command fails, configure your credentials. See [Configuration and credential file settings in the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) documentation.

**Attach Required Permissions**

Your IAM user or role needs permissions to use Code Interpreter. Attach this policy to your IAM identity:

**Note**: Replace `<region>` with your chosen region (e.g., `us-west-2`) and `<account_id>` with your AWS account ID in the policy below:

```json
{
    "Version":"2012-10-17",
    "Statement": [
        {
            "Sid": "BedrockAgentCoreCodeInterpreterFullAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:CreateCodeInterpreter",
                "bedrock-agentcore:StartCodeInterpreterSession",
                "bedrock-agentcore:InvokeCodeInterpreter",
                "bedrock-agentcore:StopCodeInterpreterSession",
                "bedrock-agentcore:DeleteCodeInterpreter",
                "bedrock-agentcore:ListCodeInterpreters",
                "bedrock-agentcore:GetCodeInterpreter",
                "bedrock-agentcore:GetCodeInterpreterSession",
                "bedrock-agentcore:ListCodeInterpreterSessions"
            ],
            "Resource": "arn:aws:bedrock-agentcore:<region>:<account_id>:code-interpreter/*"
        }
    ]
}
```

**To attach this policy**:

1. Navigate to the IAM Console
2. Find your user or role (the one returned by `aws sts get-caller-identity`)
3. Click "Add permissions" → "Create inline policy"
4. Switch to JSON view and paste the policy above
5. Name it `AgentCoreCodeInterpreterAccess` and save

>Note: If you're deploying agents to AgentCore Runtime (not covered in this guide), you'll also need to create an IAM execution role with a service trust policy. See the AgentCore Runtime QuickStart Guide for those requirements.

## Using Code Interpreter via AWS Strands

### Step 1: Install Dependencies

Create a project folder and install the required packages:

```bash
mkdir agentcore-tools-quickstart
cd agentcore-tools-quickstart
python3 -m venv .venv
source .venv/bin/activate
```

On Windows, use: `.venv\Scripts\activate`

Install the required packages:

```bash
pip install bedrock-agentcore strands-agents strands-agents-tools
```

These packages provide:

* `bedrock-agentcore`: The SDK for AgentCore tools including Code Interpreter
* `strands-agents`: The Strands agent framework
* `strands-agents-tools`: The tools that the Strands agent framework offers

### Step 2: Create Your Agent with Code Interpreter

Create a file named `code_interpreter_agent.py` and add the following code:

```python
from strands import Agent
from strands_tools.code_interpreter import AgentCoreCodeInterpreter

# Initialize the Code Interpreter tool
code_interpreter_tool = AgentCoreCodeInterpreter(region="us-west-2")

# Define the agent's system prompt
SYSTEM_PROMPT = """You are an AI assistant that validates answers through code execution.
When asked about code, algorithms, or calculations, write Python code to verify your answers."""

# Create an agent with the Code Interpreter tool
agent = Agent(
    tools=[code_interpreter_tool.code_interpreter],
    system_prompt=SYSTEM_PROMPT
)

# Test the agent with a sample prompt
prompt = "Calculate the first 10 Fibonacci numbers."
print(f"\\nPrompt: {prompt}\\n")

response = agent(prompt)
print(response.message["content"][0]["text"])
```

This code:

* Initializes the Code Interpreter tool for the `us-west-2` region
* Creates an agent configured to use code execution for validation
* Sends a prompt asking the agent to calculate Fibonacci numbers
* Prints the agent's response

### Step 3: Run the Agent

Execute the script:

```bash
python code_interpreter_agent.py
```

**Expected Output**: You should see the agent's response containing the first 10 Fibonacci numbers. The agent will write Python code to calculate the sequence and return both the code and the results.

If you encounter errors, verify:

* Your IAM role has the correct permissions and trust policy
* You have model access enabled in the Amazon Bedrock console
* Your AWS credentials are properly configured

## Using Code Interpreter Directly

### Step 1: Choose Your Approach & Install Dependencies

You can use Code Interpreter directly without an agent framework. This is useful when you want to execute specific code snippets programmatically. AgentCore provides two ways to interact with Code Interpreter: using the high-level SDK client or using boto3 directly.

* **SDK Client**: The `bedrock_agentcore` SDK provides a simplified interface that handles session management details. Use this approach for most applications.
* **Boto3 Client**: The AWS SDK gives you direct access to the Code Interpreter API operations. Use this approach when you need fine-grained control over session configuration or want to integrate with existing boto3-based applications.

Create a project folder (if you didn't create one before) and install the required packages:

```bash
mkdir agentcore-tools-quickstart
cd agentcore-tools-quickstart
python3 -m venv .venv
source .venv/bin/activate
```

On Windows, use: `.venv\Scripts\activate`

Install the required packages:

```bash
pip install bedrock-agentcore boto3
```

These packages provide:

* `bedrock-agentcore`: The SDK for AgentCore tools including Code Interpreter
* `boto3`: AWS SDK for Python (Boto3) to create, configure, and manage AWS services

### Step 2: Execute Code with the SDK Client

Create a file named `direct_code_execution_sdk.py` and add the following code:

```python
from bedrock_agentcore.tools.code_interpreter_client import CodeInterpreter
import json

# Initialize the Code Interpreter client for us-west-2
code_client = CodeInterpreter('us-west-2')

# Start a Code Interpreter session
code_client.start()

try:
    # Execute Python code
    response = code_client.invoke("executeCode", {
        "language": "python",
        "code": 'print("Hello World!!!")'
    })

    # Process and print the response
    for event in response["stream"]:
        print(json.dumps(event["result"], indent=2))

finally:
    # Always clean up the session
    code_client.stop()
```

This code:

* Creates a Code Interpreter client for your region
* Starts a session (required before executing code)
* Executes Python code and streams the results with full event details
* Stops the session to clean up resources

**Run the script**:

```bash
python direct_code_execution_sdk.py
```

**Expected Output**: You should see a JSON response containing the execution result with `Hello World!!!` in the output content.

### Step 3: Execute Code with Boto3

Create a file named `direct_code_execution_boto3.py` and add the following code:

```python
import boto3
import json

# Code to execute
code_to_execute = """
print("Hello World!!!")
"""

# Initialize the bedrock-agentcore client
client = boto3.client(
    "bedrock-agentcore",
    region_name="us-west-2"
)

# Start a Code Interpreter session
session_response = client.start_code_interpreter_session(
    codeInterpreterIdentifier="aws.codeinterpreter.v1",
    name="my-code-session",
    sessionTimeoutSeconds=900
)
session_id = session_response["sessionId"]

print(f"Started session: {session_id}\\n")

try:
    # Execute code in the session
    execute_response = client.invoke_code_interpreter(
        codeInterpreterIdentifier="aws.codeinterpreter.v1",
        sessionId=session_id,
        name="executeCode",
        arguments={
            "language": "python",
            "code": code_to_execute
        }
    )

    # Extract and print the text output from the stream
    for event in execute_response['stream']:
        if 'result' in event:
            result = event['result']
            if 'content' in result:
                for content_item in result['content']:
                    if content_item['type'] == 'text':
                        print(content_item['text'])

finally:
    # Stop the session when done
    client.stop_code_interpreter_session(
        codeInterpreterIdentifier="aws.codeinterpreter.v1",
        sessionId=session_id
    )
    print(f"\\nStopped session: {session_id}")
```

This code:

* Creates a boto3 client for the bedrock-agentcore service
* Starts a Code Interpreter session with a 900-second timeout
* Executes Python code using the session ID
* Parses the streaming response to extract text output
* Properly stops the session to release resources

The boto3 approach requires explicit session management. You must call `start_code_interpreter_session` before executing code and `stop_code_interpreter_session` when finished.

**Run the script**:

```bash
python direct_code_execution_boto3.py
```

**Expected Output**: You should see `Hello World!!!` printed as the result of the code execution, along with the session ID information.

## Common Issues & Solutions

<details>
<summary>Permission denied errors</summary>

**Symptom**: Errors mentioning access denied or insufficient permissions when starting sessions or executing code.

**Solution**:

* Verify your IAM user or role has the required Code Interpreter permissions
* Check your AWS credentials: `aws sts get-caller-identity`
* Ensure the policy includes all necessary actions: `StartCodeInterpreterSession`, `InvokeCodeInterpreter`, `StopCodeInterpreterSession`
* Verify the Resource ARN matches your region and account ID
</details>

<details>
<summary>Model access denied</summary>

**Symptom**: Errors about model access or authorization when running agents with Code Interpreter.

**Solution**:

* Navigate to the Amazon Bedrock console
* Go to **Model access** in the left navigation
* Enable **Anthropic Claude Sonnet 4**
* Verify you're in the correct region (match the region in your code)
</details>

<details>
<summary>Code execution timeout</summary>

**Symptom**: Long-running code execution fails or sessions terminate unexpectedly.

**Solution**:

* Check the `sessionTimeoutSeconds` parameter when starting sessions
* Default timeout is 900 seconds (15 minutes)
* For long-running operations, increase timeout: `sessionTimeoutSeconds=3600` (1 hour)
* Maximum timeout is 28,800 seconds (8 hours)
* Sessions automatically terminate after the timeout period
</details>

<details>
<summary>Package/library not available</summary>

**Symptom**: ImportError when trying to use specific Python packages or libraries.

**Solution**:

* AgentCore Code Interpreter comes with pre-installed common libraries (numpy, pandas, matplotlib, etc.)
* Check if the package you need is in the pre-built runtime
* For custom packages, you may need to create a custom Code Interpreter with your own environment
* Consider using built-in alternatives if your required package is not available
* Review the Code Interpreter documentation for the list of available libraries
</details>
