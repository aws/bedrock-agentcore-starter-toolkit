End-to-End Weather Agent with Tools and Memory

This CloudFormation template deploys a complete Amazon Bedrock AgentCore Runtime with a sophisticated weather-based activity planning agent. This demonstrates the full power of AgentCore by integrating Browser tool, Code Interpreter, Memory, and S3 storage in a single deployment.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Deployment](#deployment)
- [Testing](#testing)
- [Sample Queries](#sample-queries)
- [How It Works](#how-it-works)
- [Cleanup](#cleanup)
- [Cost Estimate](#cost-estimate)
- [Troubleshooting](#troubleshooting)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

## Overview

This template creates a comprehensive AgentCore deployment that showcases:

### Core Components

- **AgentCore Runtime**: Hosts a Strands agent with multiple tools
- **Browser Tool**: Web automation for scraping weather data from weather.gov
- **Code Interpreter**: Python code execution for weather analysis
- **Memory**: Stores user activity preferences
- **S3 Bucket**: Stores generated activity recommendations
- **ECR Repository**: Container image storage
- **IAM Roles**: Comprehensive permissions for all components

### Agent Capabilities

The Weather Activity Planner agent can:

1. **Scrape Weather Data**: Uses browser automation to fetch 8-day forecasts from weather.gov
1. **Analyze Weather**: Generates and executes Python code to classify days as GOOD/OK/POOR
1. **Retrieve Preferences**: Accesses user activity preferences from memory
1. **Generate Recommendations**: Creates personalized activity suggestions based on weather and preferences
1. **Store Results**: Saves recommendations as Markdown files in S3

### Use Cases

- Weather-based activity planning
- Automated web scraping and data analysis
- Multi-tool agent orchestration
- Memory-driven personalization
- Asynchronous task processing

## Architecture

The architecture demonstrates a complete AgentCore deployment with multiple integrated tools:

**Core Components:**

- **User**: Sends weather-based activity planning queries
- **AWS CodeBuild**: Builds the ARM64 Docker container image with the agent code
- **Amazon ECR Repository**: Stores the container image
- **AgentCore Runtime**: Hosts the Weather Activity Planner Agent
- **Weather Agent**: Strands agent that orchestrates multiple tools
- Invokes Amazon Bedrock LLMs for reasoning and code generation
- **Browser Tool**: Web automation for scraping weather data from weather.gov
- **Code Interpreter Tool**: Executes Python code for weather analysis
- **Memory**: Stores user activity preferences (30-day retention)
- **S3 Bucket**: Stores generated activity recommendations
- **IAM Roles**: Comprehensive permissions for all components

**Workflow:**

1. User sends query: "What should I do this weekend in Richmond VA?"
1. Agent extracts city and uses Browser Tool to scrape 8-day forecast
1. Agent generates Python code and uses Code Interpreter to classify weather
1. Agent retrieves user preferences from Memory
1. Agent generates personalized recommendations
1. Agent stores results in S3 bucket using use_aws tool

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
1. [Bedrock Model Access Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html)
1. **Required Permissions**: Your AWS user/role needs permissions for:
1. CloudFormation stack operations
1. ECR repository management
1. IAM role creation
1. Lambda function creation
1. CodeBuild project creation
1. BedrockAgentCore resource creation (Runtime, Browser, CodeInterpreter, Memory)
1. S3 bucket creation

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
1. Display all resource IDs (Runtime, Browser, CodeInterpreter, Memory, S3 Bucket)

### Option 2: Using AWS CLI

```
# Deploy the stack
aws cloudformation create-stack \
  --stack-name weather-agent-demo \
  --template-body file://end-to-end-weather-agent.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-west-2

# Wait for stack creation
aws cloudformation wait stack-create-complete \
  --stack-name weather-agent-demo \
  --region us-west-2

# Get all outputs
aws cloudformation describe-stacks \
  --stack-name weather-agent-demo \
  --region us-west-2 \
  --query 'Stacks[0].Outputs'
```

### Option 3: Using AWS Console

1. Navigate to [CloudFormation Console](https://console.aws.amazon.com/cloudformation/)
1. Click "Create stack" → "With new resources"
1. Upload the `end-to-end-weather-agent.yaml` file
1. Enter stack name: `weather-agent-demo`
1. Review parameters (or use defaults)
1. Check "I acknowledge that AWS CloudFormation might create IAM resources"
1. Click "Create stack"

### Deployment Time

- **Expected Duration**: 15-20 minutes
- **Main Steps**:
- Stack creation: ~2 minutes
- Docker image build (CodeBuild): ~10-12 minutes
- Runtime and tools provisioning: ~3-5 minutes
- Memory initialization: ~1 minute

## Testing

### Using AWS CLI

```
# Get the Runtime ID from stack outputs and construct ARN
RUNTIME_ID=$(aws cloudformation describe-stacks \
  --stack-name weather-agent-demo \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentRuntimeId`].OutputValue' \
  --output text)

# Get account ID and construct the ARN
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-west-2"
RUNTIME_ARN="arn:aws:bedrock-agentcore:${REGION}:${ACCOUNT_ID}:runtime/${RUNTIME_ID}"

# Get the S3 bucket name
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name weather-agent-demo \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`ResultsBucket`].OutputValue' \
  --output text)

# Prepare the payload (base64 encoded, note the -n flag)
PAYLOAD=$(echo -n '{"prompt": "What should I do this weekend in Richmond VA?"}' | base64)

# Invoke the agent
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn $RUNTIME_ARN \
  --qualifier DEFAULT \
  --payload $PAYLOAD \
  --region us-west-2 \
  response.json

# View the immediate response
cat response.json

# Wait a few minutes for processing, then check S3 for results
aws s3 ls s3://$BUCKET_NAME/

# Download the results
aws s3 cp s3://$BUCKET_NAME/results.md ./results.md
cat results.md
```

### Using AWS Console

1. Navigate to [Bedrock AgentCore Console](https://console.aws.amazon.com/bedrock-agentcore/)

1. Go to "Runtimes" in the left navigation

1. Find your runtime (name starts with `weather_agent_demo_`)

1. Click on the runtime name

1. Click "Test" button

1. Enter test payload:

   ```
   {
     "prompt": "What should I do this weekend in Richmond VA?"
   }
   ```

1. Click "Invoke"

1. View the immediate response

1. Wait 2-3 minutes for background processing

1. Navigate to [S3 Console](https://console.aws.amazon.com/s3/) to download results.md from the results bucket

## Sample Queries

Try these queries to test the weather agent:

1. **Weekend Planning**:

   ```
   {"prompt": "What should I do this weekend in Richmond VA?"}
   ```

1. **Specific City**:

   ```
   {"prompt": "Plan activities for next week in San Francisco"}
   ```

1. **Different Location**:

   ```
   {"prompt": "What outdoor activities can I do in Seattle this week?"}
   ```

1. **Vacation Planning**:

   ```
   {"prompt": "I'm visiting Austin next week. What should I plan based on the weather?"}
   ```

## How It Works

### Step-by-Step Workflow

1. **User Query**: "What should I do this weekend in Richmond VA?"

1. **City Extraction**: Agent extracts "Richmond VA" from the query

1. **Weather Scraping** (Browser Tool):

1. Navigates to weather.gov

1. Searches for Richmond VA

1. Clicks "Printable Forecast"

1. Extracts 8-day forecast data (date, high, low, conditions, wind, precipitation)

1. Returns JSON array of weather data

1. **Code Generation** (LLM):

1. Agent generates Python code to classify weather days

1. Classification rules:

   - GOOD: 65-80°F, clear, no rain
   - OK: 55-85°F, partly cloudy, slight rain
   - POOR: \<55°F or >85°F, cloudy/rainy

1. **Code Execution** (Code Interpreter):

1. Executes the generated Python code

1. Returns list of tuples: `[('2025-09-16', 'GOOD'), ('2025-09-17', 'OK'), ...]`

1. **Preference Retrieval** (Memory):

1. Fetches user activity preferences from memory

1. Preferences stored by weather type:

   ```
   {
     "good_weather": ["hiking", "beach volleyball", "outdoor picnic"],
     "ok_weather": ["walking tours", "outdoor dining", "park visits"],
     "poor_weather": ["indoor museums", "shopping", "restaurants"]
   }
   ```

1. **Recommendation Generation** (LLM):

1. Combines weather analysis with user preferences

1. Creates day-by-day activity recommendations

1. Formats as Markdown document

1. **Storage** (S3 via use_aws tool):

1. Saves recommendations to S3 bucket as `results.md`

1. User can download and review recommendations

### Asynchronous Processing

The agent runs asynchronously to handle long-running tasks:

- Immediate response: "Processing started..."
- Background processing: Completes all steps
- Results available in S3 after ~2-3 minutes

## Cleanup

### Using the Cleanup Script (Recommended)

```
# Make the script executable
chmod +x cleanup.sh

# Delete the stack
./cleanup.sh
```

**Note**: If cleanup fails due to active browser sessions, see the AWS CLI cleanup method below for manual session termination.

### Using AWS CLI

```
# Step 1: Empty the S3 bucket (required before deletion)
BUCKET_NAME=$(aws cloudformation describe-stacks \
  --stack-name weather-agent-demo \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`ResultsBucket`].OutputValue' \
  --output text)

aws s3 rm s3://$BUCKET_NAME --recursive

# Step 2: Terminate any active browser sessions
# Get the Browser ID
BROWSER_ID=$(aws cloudformation describe-stacks \
  --stack-name weather-agent-demo \
  --region us-west-2 \
  --query 'Stacks[0].Outputs[?OutputKey==`BrowserId`].OutputValue' \
  --output text)

# List active sessions
aws bedrock-agentcore list-browser-sessions \
  --browser-id $BROWSER_ID \
  --region us-west-2

# Terminate each active session (replace SESSION_ID with actual session ID from list command)
# Repeat this command for each active session
aws bedrock-agentcore terminate-browser-session \
  --browser-id $BROWSER_ID \
  --session-id SESSION_ID \
  --region us-west-2

# Step 3: Delete the stack
aws cloudformation delete-stack \
  --stack-name weather-agent-demo \
  --region us-west-2

# Wait for deletion to complete
aws cloudformation wait stack-delete-complete \
  --stack-name weather-agent-demo \
  --region us-west-2
```

**Important**: Browser sessions are automatically created when the agent uses the browser tool. Always terminate active sessions before deleting the stack to avoid deletion failures.

### Using AWS Console

1. Navigate to [S3 Console](https://console.aws.amazon.com/s3/)
1. Find the bucket (name format: `<stack-name>-results-<account-id>`, e.g., `weather-agent-demo-results-123456789012`)
1. Empty the bucket
1. Navigate to [Bedrock AgentCore Console](https://console.aws.amazon.com/bedrock-agentcore/)
1. Go to "Browsers" in the left navigation
1. Find your browser (name starts with `weather_agent_demo_browser`)
1. Click on the browser name
1. In the "Sessions" tab, terminate any active sessions
1. Navigate to [CloudFormation Console](https://console.aws.amazon.com/cloudformation/)
1. Select the `weather-agent-demo` stack
1. Click "Delete"
1. Confirm deletion
