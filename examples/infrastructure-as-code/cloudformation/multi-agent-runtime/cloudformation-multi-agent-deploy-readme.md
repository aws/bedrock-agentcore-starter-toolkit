Multi-Agent AgentCore Runtime

This CloudFormation template demonstrates a multi-agent architecture where one agent (orchestrator) can invoke another agent (specialist) to handle complex tasks. This pattern is useful for building sophisticated AI systems with specialized capabilities.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Deployment](#deployment)
- [Testing](#testing)
- [Sample Queries](#sample-queries)
- [Cleanup](#cleanup)
- [Cost Estimate](#cost-estimate)
- [Troubleshooting](#troubleshooting)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

## Overview

This template creates a two-agent system that demonstrates agent-to-agent communication:

### Agent 1: Orchestrator Agent

- **Role**: Main entry point for user queries
- **Capabilities**:
- Handles simple queries directly
- Delegates complex tasks to Agent 2
- Has a tool to invoke Agent 2's runtime
- **Use Cases**: Routing, task delegation, simple Q&A

### Agent 2: Specialist Agent

- **Role**: Expert agent for detailed analysis
- **Capabilities**:
- Provides in-depth analytical responses
- Handles complex reasoning tasks
- Focuses on accuracy and completeness
- **Use Cases**: Data analysis, expert knowledge, detailed explanations

### Key Features

- **Multi-Agent Communication**: Agent 1 can invoke Agent 2 using `bedrock-agentcore:InvokeAgentRuntime`
- **Automatic Orchestration**: Agent 1 decides when to delegate based on query complexity
- **Independent Deployment**: Each agent has its own ECR repository and runtime
- **Modular Architecture**: Easy to extend with additional specialized agents

## Architecture

The architecture consists of:

- **User**: Sends questions to Agent 1 (Orchestrator) and receives responses
- **Agent 1 - Orchestrator Agent**:
- **AWS CodeBuild**: Builds the ARM64 Docker container image for Agent 1
- **Amazon ECR Repository**: Stores Agent 1's container image
- **AgentCore Runtime**: Hosts the Orchestrator Agent
  - Routes simple queries directly
  - Delegates complex queries to Agent 2 using the `call_specialist_agent` tool
  - Invokes Amazon Bedrock LLMs for reasoning
- **IAM Role**: Permissions to invoke Agent 2's runtime and access Bedrock
- **Agent 2 - Specialist Agent**:
- **AWS CodeBuild**: Builds the ARM64 Docker container image for Agent 2
- **Amazon ECR Repository**: Stores Agent 2's container image
- **AgentCore Runtime**: Hosts the Specialist Agent
  - Provides detailed analysis and expert responses
  - Invokes Amazon Bedrock LLMs for in-depth reasoning
- **IAM Role**: Standard runtime permissions and Bedrock access
- **Amazon Bedrock LLMs**: Provides AI model capabilities for both agents
- **Agent-to-Agent Communication**: Agent 1 can invoke Agent 2's runtime via `bedrock-agentcore:InvokeAgentRuntime` API

## Prerequisites

### AWS Account Setup

1. **AWS Account**: You need an active AWS account with appropriate permissions
1. [Create AWS Account](https://aws.amazon.com/account/)
1. [AWS Console Access](https://aws.amazon.com/console/)
1. **AWS CLI**: Install and configure AWS CLI with your credentials
1. [Install AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
1. [Configure AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-quickstart.html)

```
aws configure
```

1. **Bedrock Model Access**: Enable access to Amazon Bedrock models in your AWS region
1. Navigate to [Amazon Bedrock Console](https://console.aws.amazon.com/bedrock/)
1. Go to "Model access" and request access to:
   - Anthropic Claude models
1. [Bedrock Model Access Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)
1. **Required Permissions**: Your AWS user/role needs permissions for:
1. CloudFormation stack operations
1. ECR repository management
1. IAM role creation
1. Lambda function creation
1. CodeBuild project creation
1. BedrockAgentCore resource creation

## Deployment

### Option 1: Using the Deploy Script (Recommended)

```
# Make the script executable
chmod +x deploy.sh

# Deploy the stack
./deploy.sh
```

The script will:

1. Deploy the CloudFormation stack
1. Wait for stack creation to complete
1. Display both Agent Runtime IDs

### Option 2: Using AWS CLI

```
# Deploy the stack
aws cloudformation create-stack \
  --stack-name multi-agent-demo \
  --template-body file://template.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-west-2

# Wait for stack creation
aws cloudformation wait stack-create-complete \
  --stack-name multi-agent-demo \
  --region us-west-2

# Get the Runtime IDs
aws cloudformation describe-stacks \
  --stack-name multi-agent-demo \
  --region us-west-2 \
  --query 'Stacks[0].Outputs'
```

### Option 3: Using AWS Console

1. Navigate to [CloudFormation Console](https://console.aws.amazon.com/cloudformation/)
1. Click "Create stack" → "With new resources"
1. Upload the `template.yaml` file
1. Enter stack name: `multi-agent-demo`
1. Review parameters (or use defaults)
1. Check "I acknowledge that AWS CloudFormation might create IAM resources"
1. Click "Create stack"

## Testing

### Test Agent 1 (Orchestrator)

Agent 1 is your main entry point. It will handle simple queries directly or delegate to Agent 2 for complex tasks.

#### Using AWS CLI

```
# Get Agent1 Runtime ID
AGENT1_ID=$(aws cloudformation describe-stacks \
  --stack-name multi-agent-demo \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`Agent1RuntimeId`].OutputValue' \
  --output text)

# Test with a simple query (Agent1 handles directly)
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-id $AGENT1_ID \
  --qualifier DEFAULT \
  --payload '{"prompt": "Hello, how are you?"}' \
  --region us-west-2 \
  response.json

# Test with a complex query (Agent1 delegates to Agent2)
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-id $AGENT1_ID \
  --qualifier DEFAULT \
  --payload '{"prompt": "Provide a detailed analysis of cloud computing benefits"}' \
  --region us-west-2 \
  response.json

cat response.json
```

### Using AWS Console

1. Navigate to [Bedrock AgentCore Console](https://console.aws.amazon.com/bedrock-agentcore/)

1. Go to "Runtimes" in the left navigation

1. Find Agent1 runtime (name starts with `multi_agent_demo_OrchestratorAgent`)

1. Click on the runtime name

1. Click "Test" button

1. Enter test payload:

   ```
   {
     "prompt": "Hello, how are you?"
   }
   ```

1. Click "Invoke"

### Test Agent 2 (Specialist) Directly

You can also test Agent 2 directly to see its specialized capabilities.

```
# Get Agent2 Runtime ID
AGENT2_ID=$(aws cloudformation describe-stacks \
  --stack-name multi-agent-demo \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`Agent2RuntimeId`].OutputValue' \
  --output text)

# Invoke Agent2 directly
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-id $AGENT2_ID \
  --qualifier DEFAULT \
  --payload '{"prompt": "Explain quantum computing in detail"}' \
  --region us-west-2 \
  response.json
```

## Sample Queries

### Queries that Agent 1 Handles Directly

These simple queries don't require specialist knowledge:

1. **Greetings**:

   ```
   {"prompt": "Hello, how are you?"}
   ```

1. **Simple Math**:

   ```
   {"prompt": "What is 5 + 3?"}
   ```

### Queries that Trigger Agent 2 Delegation

These complex queries require expert analysis:

1. **Detailed Analysis**:

   ```
   {"prompt": "Provide a detailed analysis of the benefits and drawbacks of serverless architecture"}
   ```

1. **Expert Knowledge**:

   ```
   {"prompt": "Explain the CAP theorem and its implications for distributed systems"}
   ```

1. **Complex Reasoning**:

   ```
   {"prompt": "Compare and contrast different machine learning algorithms for time series forecasting"}
   ```

1. **In-depth Explanation**:

   ```
   {"prompt": "Provide expert analysis on best practices for securing cloud infrastructure"}
   ```

## Cleanup

### Using the Cleanup Script (Recommended)

```
# Make the script executable
chmod +x cleanup.sh

# Delete the stack
./cleanup.sh
```

### Using AWS CLI

```
aws cloudformation delete-stack \
  --stack-name multi-agent-demo \
  --region us-west-2

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete \
  --stack-name multi-agent-demo \
  --region us-west-2
```

### Using AWS Console

1. Navigate to [CloudFormation Console](https://console.aws.amazon.com/cloudformation/)
1. Select the `multi-agent-demo` stack
1. Click "Delete"
1. Confirm deletion
