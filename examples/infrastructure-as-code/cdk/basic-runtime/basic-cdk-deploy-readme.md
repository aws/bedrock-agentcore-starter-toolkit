Basic AgentCore Runtime - CDK

This CDK stack deploys a basic Amazon Bedrock AgentCore Runtime with a simple Strands agent. This is the simplest possible AgentCore deployment, perfect for getting started and understanding the core concepts without additional complexity.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Deployment](#deployment)
- [Testing](#testing)
- [Sample Queries](#sample-queries)
- [Cleanup](#cleanup)
- [Troubleshooting](#troubleshooting)

## Overview

This CDK stack creates a minimal AgentCore deployment that includes:

- **AgentCore Runtime**: Hosts a simple Strands agent
- **ECR Repository**: Stores the Docker container image
- **IAM Roles**: Provides necessary permissions
- **CodeBuild Project**: Automatically builds the ARM64 Docker image
- **Lambda Functions**: Custom resources for automation
- **S3 Assets**: Source code packaging and deployment

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

1. **Python 3.10+** and **AWS CDK v2** installed

   ```
   # Install CDK
   npm install -g aws-cdk

   # Verify installation
   cdk --version
   ```

1. **CDK version 2.218.0 or later** (for BedrockAgentCore support)

1. **Bedrock Model Access**: Enable access to Amazon Bedrock models in your AWS region

1. [Bedrock Model Access Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)

1. **Required Permissions**: Your AWS user/role needs permissions for:

1. CloudFormation stack operations

1. ECR repository management

1. IAM role creation

1. Lambda function creation

1. CodeBuild project creation

1. BedrockAgentCore resource creation

1. S3 bucket operations (for CDK assets)

## Deployment

### Option 1: Quick Deploy (Recommended)

```
# Install dependencies
pip install -r requirements.txt

# Bootstrap CDK (first time only)
cdk bootstrap

# Deploy
cdk deploy
```

### Option 2: Step by Step

```
# 1. Create and activate Python virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 2. Bootstrap CDK in your account/region (first time only)
cdk bootstrap

# 3. Synthesize the CloudFormation template (optional)
cdk synth

# 4. Deploy the stack
cdk deploy --require-approval never

# 5. Get outputs
cdk list
```

### Deployment Time

- **Expected Duration**: 3-5 minutes

## Testing

### Using AWS CLI

```
# Get the Runtime ARN from CDK outputs
RUNTIME_ARN=$(aws cloudformation describe-stacks \
  --stack-name BasicAgentDemo \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentRuntimeArn`].OutputValue' \
  --output text)

# Invoke the agent
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn $RUNTIME_ARN \
  --qualifier DEFAULT \
  --payload $(echo '{"prompt": "What is 2+2?"}' | base64) \
  response.json

# View the response
cat response.json
```

### Using AWS Console

1. Navigate to [Bedrock AgentCore Console](https://console.aws.amazon.com/bedrock-agentcore/)

1. Go to "Runtimes" in the left navigation

1. Find your runtime (name starts with `BasicAgentDemo_`)

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

### Using CDK (Recommended)

```
cdk destroy
```

### Using AWS CLI

```
aws cloudformation delete-stack \
  --stack-name BasicAgentDemo \
  --region us-east-1

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete \
  --stack-name BasicAgentDemo \
  --region us-east-1
```

### Using AWS Console

1. Navigate to [CloudFormation Console](https://console.aws.amazon.com/cloudformation/)
1. Select the `BasicAgentDemo` stack
1. Click "Delete"
1. Confirm deletion

## Troubleshooting

### CDK Bootstrap Required

If you see bootstrap errors:

```
cdk bootstrap aws://ACCOUNT-NUMBER/REGION
```

### Permission Issues

Ensure your IAM user/role has:

- `CDKToolkit` permissions or equivalent
- Permissions to create all resources in the stack
- `iam:PassRole` for service roles

### Python Dependencies

Install dependencies in the project directory:

```
pip install -r requirements.txt
```

### Build Failures

Check CodeBuild logs in the AWS Console:

1. Go to CodeBuild console
1. Find the build project (name contains "basic-agent-build")
1. Check build history and logs
