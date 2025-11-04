# QuickStart: Your First Agent in 5 Minutes! 🚀

This tutorial shows you how to use the Amazon Bedrock AgentCore [starter toolkit](https://github.com/aws/bedrock-agentcore-starter-toolkit) to deploy an agent to an AgentCore Runtime.

The starter toolkit is a Command Line Interface (CLI) toolkit that you can use to deploy AI agents to an AgentCore Runtime. You can use the toolkit with popular Python agent frameworks, such as LangGraph or [Strands Agents](https://strandsagents.com/latest/documentation/docs/). This tutorial uses Strands Agents.

## Prerequisites

Before you start, make sure you have:

- **AWS Account** with credentials configured. To configure your AWS credentials, see [Configuration and credential file settings in the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html).
- **Python 3.10+** installed
- [Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/quickstart.html) installed
- **AWS Permissions**: To create and deploy an agent with the starter toolkit, you must have appropriate permissions. For information, see [Use the starter toolkit](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html#runtime-permissions-starter-toolkit).
- **Model access**: Anthropic Claude Sonnet 4.0 [enabled](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access-modify.html) in the Amazon Bedrock console. For information about using a different model with the Strands Agents see the *Model Providers* section in the [Strands Agents SDK](https://strandsagents.com/latest/documentation/docs/) documentation.

## Step 1: Setup Project and Install Dependencies

Create a project folder and install the required packages:

```bash
mkdir agentcore-runtime-quickstart
cd agentcore-runtime-quickstart
python3 -m venv .venv
source .venv/bin/activate
```

> On Windows, use: `.venv\Scripts\activate`

Upgrade pip to the latest version:

```bash
pip install --upgrade pip
```

Install the following required packages:

- **bedrock-agentcore** - The Amazon Bedrock AgentCore SDK for building AI agents
- **strands-agents** - The [Strands Agents](https://strandsagents.com/latest/) SDK
- **bedrock-agentcore-starter-toolkit** - The Amazon Bedrock AgentCore starter toolkit

```bash
pip install bedrock-agentcore strands-agents bedrock-agentcore-starter-toolkit
```

Verify installation:

```bash
agentcore --help
```

## Step 2: Create Your Agent

Create a source file for your agent code named `my_agent.py`. Add the following code:

```python
from bedrock_agentcore import BedrockAgentCoreApp
from strands import Agent

app = BedrockAgentCoreApp()
agent = Agent()

@app.entrypoint
def invoke(payload):
    """Your AI agent function"""
    user_message = payload.get("prompt", "Hello! How can I help you today?")
    result = agent(user_message)
    return {"result": result.message}

if __name__ == "__main__":
    app.run()
```

Create `requirements.txt` and add the following:

```
bedrock-agentcore
strands-agents
```

## Step 3: Test Locally

Open a terminal window and start your agent with the following command:

```bash
python my_agent.py
```

Test your agent by opening another terminal window and enter the following command:

```bash
curl -X POST http://localhost:8080/invocations \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello!"}'
```

**Success:** You should see a response like `{"result": "Hello! I'm here to help..."}`.

In the terminal window that's running the agent, enter `Ctrl+C` to stop the agent.

> Important: Make sure port 8080 is free before starting.

## Step 4: Configure Your Agent

Configure and deploy your agent to AWS using the starter toolkit. The toolkit automatically creates the IAM execution role, container image (for container deployment), or S3 bucket (for direct_code_deploy deployment), and other resources needed to host the agent in AgentCore Runtime. By default the toolkit uses direct_code_deploy deployment and hosts the agent in an AgentCore Runtime that is in the `us-west-2` AWS Region.

Configure the agent. Use the default values:

```bash
agentcore configure -e my_agent.py
```

- The `-e` or `--entrypoint` flag specifies the entrypoint file for your agent (the Python file containing your agent code)
- This command creates configuration for deployment to AWS
- Accept the default values unless you have specific requirements
- The configuration information is stored in a hidden file named `.bedrock_agentcore.yaml`
- During configuration, you'll be prompted to choose memory options. Memory will be provisioned based on your choice: short-term memory (STM) only, or both short-term and long-term memory (LTM) with automatic extraction of facts, preferences, and summaries.

> **Note**: To continue without memory, use the `--disable-memory` flag: `agentcore configure -e my_agent.py --disable-memory`

### Using a Different Region

By default, the toolkit deploys to `us-west-2`. To use a different region:

```bash
agentcore configure -e my_agent.py -r us-east-1
```

## Step 5: Enable Observability for Your Agent

[Amazon Bedrock AgentCore Observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability.html) helps you trace, debug, and monitor agents that you host in AgentCore Runtime. First enable CloudWatch Transaction Search by following the instructions at [Enabling AgentCore runtime observability](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html#observability-configure-builtin). To observe your agent, see [View observability data for your Amazon Bedrock AgentCore agents](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-view.html).

## Step 6: Deploy to AgentCore Runtime

Host your agent in AgentCore Runtime:

```bash
agentcore launch
```

This command:

- Builds your container using AWS CodeBuild (no Docker required locally) for container deployment, or packages Python code for direct_code_deploy deployment (default)
- Creates necessary AWS resources (ECR repository for containers, S3 bucket for direct_code_deploy, IAM roles, etc.)
- Deploys your agent to AgentCore Runtime
- Creates memory resources if you configured memory during the setup
- Configures CloudWatch logging

In the output from `agentcore launch` note the following:

- The Amazon Resource Name (ARN) of the agent. You need it to invoke the agent with the InvokeAgentRuntime operation.
- The location of the logs in Amazon CloudWatch Logs

If the deployment fails check for Common Issues.

For other deployment options, see Deployment Modes.

> **Note**: Before invoking your agent, you can check the deployment status using `agentcore status` to verify that all resources including memory (if configured) are provisioned and ready.

## Step 7: Test Your Deployed Agent

Test your deployed agent:

```bash
agentcore invoke '{"prompt": "tell me a joke"}'
```

If you see a joke in the response, your agent is now running in an AgentCore Runtime and can be invoked. If not, check for Common Issues.

## Step 8: Invoke Your Agent Programmatically

You can invoke the agent using the AWS SDK InvokeAgentRuntime operation. To call InvokeAgentRuntime, you need the ARN of the agent that you noted in Step 6: Deploy to AgentCore Runtime. You can also get the ARN from the `bedrock_agentcore:` section of the `.bedrock_agentcore.yaml` (hidden) file that the toolkit creates.

Use the following boto3 (AWS SDK) code to invoke your agent. Replace `<Add your ARN>` with the ARN of your agent. Make sure that you have `bedrock-agentcore:InvokeAgentRuntime` permissions.

Create a file named `invoke_agent.py` and add the following code:

```python
import json
import uuid
import boto3

agent_arn = "<Add your ARN>"
prompt = "Tell me a joke"

# Initialize the AgentCore client
agent_core_client = boto3.client('bedrock-agentcore')

# Prepare the payload
payload = json.dumps({"prompt": prompt}).encode()

# Invoke the agent
response = agent_core_client.invoke_agent_runtime(
    agentRuntimeArn=agent_arn,
    runtimeSessionId=str(uuid.uuid4()),
    payload=payload,
    qualifier="DEFAULT"
)

content = []
for chunk in response.get("response", []):
    content.append(chunk.decode('utf-8'))
print(json.loads(''.join(content)))
```

Open a terminal window and run the code with the following command:

```bash
python invoke_agent.py
```

If successful, you should see a joke in the response. If the call fails, check the logs that you noted in Step 6: Deploy to AgentCore Runtime.

> If you plan on integrating your agent with OAuth, you can't use the AWS SDK to call InvokeAgentRuntime. Instead, make a HTTPS request to InvokeAgentRuntime. For more information, see Authenticate and authorize with Inbound Auth and Outbound Auth.

## Step 9: Clean Up

If you no longer want to host the agent in the AgentCore Runtime, use the AgentCore console or the DeleteAgentRuntime AWS SDK operation to delete the AgentCore Runtime.

```bash
agentcore destroy
```

## Find Your Resources

After deployment, view your resources in AWS Console:

|Resource            |Location                                                                      |
|--------------------|------------------------------------------------------------------------------|
|**Agent Logs**      |CloudWatch → Log groups → `/aws/bedrock-agentcore/runtimes/{agent-id}-DEFAULT`|
|**Memory Resources**|Bedrock AgentCore → Memory (if memory was configured during setup)            |
|**Container Images**|ECR → Repositories → `bedrock-agentcore-{agent-name}` (container deployment only)|
|**S3 Deployment**   |S3 → Buckets → Your deployment bucket → `{agent-name}/deployment.zip`           |
|**IAM Role**        |IAM → Roles → Search for "BedrockAgentCore"                                   |

## Common Issues & Solutions

Common issues and solutions when getting started with the Amazon Bedrock AgentCore starter toolkit. For more troubleshooting information, see [Troubleshoot AgentCore Runtime](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-troubleshooting.html).

<details>
<summary>Permission denied errors</summary>

Verify your AWS credentials and permissions:

- Verify AWS credentials: `aws sts get-caller-identity`
- Check you have the required policies attached
- Review caller permissions policy for detailed requirements

</details>

<details>
<summary>Docker not found warnings</summary>

You can ignore this warning:

- **Ignore this!** Default deployment uses direct_code_deploy (no Docker needed), or CodeBuild for container deployment
- Only install Docker/Finch/Podman if you want to use `--local` or `--local-build` flags

</details>

<details>
<summary>Model access denied</summary>

Enable model access in the Bedrock console:

- Enable Anthropic Claude 4.0 in the Bedrock console
- Make sure you're in the correct AWS region (us-west-2 by default)

</details>

<details>
<summary>CodeBuild build error</summary>

Check build logs and permissions:

- Check CodeBuild project logs in AWS console
- Verify your caller permissions include CodeBuild access

</details>

<details>
<summary>Port 8080 in use (local only)</summary>

**Symptom**: Error stating port 8080 is already in use when testing locally.

**Solution**:

- Mac/Linux: `lsof -ti:8080 | xargs kill -9`
- Windows: Find and stop the process using port 8080 in Task Manager
- Or choose a different port in your configuration

</details>

<details>
<summary>Region mismatch</summary>

**Symptom**: Resources not found or deployment fails due to region mismatch.

**Solution**:

- Verify region with `aws configure get region`
- Ensure all resources (agent, models, etc.) are in the same region
- Use the `-r` flag during configuration to specify the correct region

</details>

<details>
<summary>Memory provisioning still in progress</summary>

**Symptom**: Error indicating memory is not yet ready when invoking the agent.

**Solution**:

- Memory provisioning can take 2-5 minutes, especially for long-term memory (LTM)
- Check status with `agentcore status` until memory shows as active
- Short-term memory (STM) is available immediately; LTM requires additional setup time

</details>

## Advanced Options (Optional)

The starter toolkit has advanced configuration options for different deployment modes and custom IAM roles. For more information, see [Runtime commands for the starter toolkit](https://aws.github.io/bedrock-agentcore-starter-toolkit/api-reference/cli.html).

### Deployment Modes

Choose the right deployment approach for your needs:

**Default: Direct Code Deploy Deployment (RECOMMENDED)**

Suitable for most use cases, no Docker required:

```bash
agentcore launch  # Uses CodeBuild for containers, .zip archive for direct deploy
```

**Local Development**

Suitable for development, rapid iteration, debugging:

```bash
agentcore launch --local  # Build and run locally (requires Docker/Finch/Podman)
```

**Hybrid: Local Build + Cloud Runtime**

Suitable for teams with Docker expertise needing build customization:

```bash
agentcore launch --local-build  # Build locally, deploy to cloud (requires Docker/Finch/Podman)
```

> Note: Docker is only required for `--local` and `--local-build` modes. The default mode uses AWS CodeBuild.

### Custom Execution Role

Use an existing IAM role:

```bash
agentcore configure -e my_agent.py --execution-role arn:aws:iam::111122223333:role/MyRole
```

### Why ARM64?

AgentCore Runtime requires ARM64 containers (AWS Graviton). The toolkit handles this automatically:

- **Default (CodeBuild)**: Builds ARM64 containers in the cloud - no Docker needed
- **Local with Docker**: Only containers built on ARM64 machines will work when deployed to agentcore runtime
