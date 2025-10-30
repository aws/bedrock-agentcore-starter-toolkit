Basic AgentCore Runtime

This CloudFormation template deploys a basic Amazon Bedrock AgentCore Runtime with a simple Strands agent. This is the simplest possible AgentCore deployment, perfect for getting started and understanding the core concepts without additional complexity.

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

This template creates a minimal AgentCore deployment that includes:

- **AgentCore Runtime**: Hosts a simple Strands agent
- **ECR Repository**: Stores the Docker container image
- **IAM Roles**: Provides necessary permissions
- **CodeBuild Project**: Automatically builds the ARM64 Docker image
- **Lambda Functions**: Custom resources for automation

This makes it ideal for:

- Learning AgentCore basics
- Quick prototyping
- Understanding the core deployment pattern
- Building a foundation before adding complexity

## Architecture

The architecture consists of:

- **User**: Sends questions to the agent and receives responses
- **AWS CodeBuild**: Builds the ARM64 Docker container image with the agent code
- **Amazon ECR Repository**: Stores the container image
- **AgentCore Runtime**: Hosts the Basic Agent container
- **Basic Agent**: Simple Strands agent that processes user queries
- Invokes Amazon Bedrock LLMs to generate responses
- **IAM Roles**:
- IAM role for CodeBuild (builds and pushes images)
- IAM role for Agent Execution (runtime permissions)
- **Amazon Bedrock LLMs**: Provides the AI model capabilities for the agent

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
1. Display the AgentCore Runtime ID

### Option 2: Using AWS CLI

```
# Deploy the stack
aws cloudformation create-stack \
  --stack-name basic-agent-demo \
  --template-body file://template.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-west-2

# Wait for stack creation
aws cloudformation wait stack-create-complete \
  --stack-name basic-agent-demo \
  --region us-west-2

# Get the Runtime ID
aws cloudformation describe-stacks \
  --stack-name basic-agent-demo \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentRuntimeId`].OutputValue' \
  --output text
```

### Option 3: Using AWS Console

1. Navigate to [CloudFormation Console](https://console.aws.amazon.com/cloudformation/)
1. Click "Create stack" → "With new resources"
1. Upload the `template.yaml` file
1. Enter stack name: `basic-agent-demo`
1. Review parameters (or use defaults)
1. Check "I acknowledge that AWS CloudFormation might create IAM resources"
1. Click "Create stack"

### Deployment Time

- **Expected Duration**: 10-15 minutes
- **Main Steps**:
- Stack creation: ~2 minutes
- Docker image build (CodeBuild): ~8-10 minutes
- Runtime provisioning: ~2-3 minutes

## Testing

### Using AWS CLI

```
# Get the Runtime ID from stack outputs
RUNTIME_ID=$(aws cloudformation describe-stacks \
  --stack-name basic-agent-demo \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentRuntimeId`].OutputValue' \
  --output text)

# Get account ID and construct the ARN
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-west-2"
RUNTIME_ARN="arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:runtime/${RUNTIME_ID}"

# Prepare the payload (base64 encoded, note the -n flag to avoid newlines)
PAYLOAD=$(echo -n '{"prompt": "What is 2+2?"}' | base64)

# Invoke the agent
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn $RUNTIME_ARN \
  --qualifier DEFAULT \
  --payload $PAYLOAD \
  --region us-west-2 \
  response.json

# View the response
cat response.json
```

### Using AWS Console

1. Navigate to [Bedrock AgentCore Console](https://console.aws.amazon.com/bedrock-agentcore/)

1. Go to "Runtimes" in the left navigation

1. Find your runtime (name starts with `basic_agent_demo_`)

1. Click on the runtime name

1. Click "Test" button

1. Enter test payload:

   ```
   {
     "prompt": "What is 2+2?"
   }
   ```

1. Click "Invoke"

## Sample Queries

Try these queries to test your basic agent:

1. **Simple Math**:

   ```
   {"prompt": "What is 2+2?"}
   ```

1. **General Knowledge**:

   ```
   {"prompt": "What is the capital of France?"}
   ```

1. **Explanation Request**:

   ```
   {"prompt": "Explain what Amazon Bedrock is in simple terms"}
   ```

1. **Creative Task**:

   ```
   {"prompt": "Write a haiku about cloud computing"}
   ```

1. **Reasoning**:

   ```
   {"prompt": "If I have 5 apples and give away 2, how many do I have left?"}
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
  --stack-name basic-agent-demo \
  --region us-west-2

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete \
  --stack-name basic-agent-demo \
  --region us-west-2
```

### Using AWS Console

1. Navigate to [CloudFormation Console](https://console.aws.amazon.com/cloudformation/)
1. Select the `basic-agent-demo` stack
1. Click "Delete"
1. Confirm deletion
