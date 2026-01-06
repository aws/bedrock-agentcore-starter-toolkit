Basic AgentCore Runtime - Terraform

This pattern demonstrates the simplest deployment of an AgentCore Runtime using Terraform. It creates a basic agent without additional tools like Memory, Code Interpreter, or Browser.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Testing the Agent](#testing-the-agent)
- [Sample Queries](#sample-queries)
- [Customization](#customization)
- [File Structure](#file-structure)
- [Troubleshooting](#troubleshooting)
- [Cleanup](#cleanup)
- [Pricing](#pricing)
- [Next Steps](#next-steps)
- [Resources](#resources)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

## Overview

This Terraform configuration creates a minimal AgentCore deployment that includes:

- **AgentCore Runtime**: Hosts a simple Strands agent
- **ECR Repository**: Stores the Docker container image
- **IAM Roles**: Provides necessary permissions
- **CodeBuild Project**: Automatically builds the ARM64 Docker image

This makes it ideal for:

- Learning AgentCore basics with Terraform
- Quick prototyping and experimentation
- Understanding the core deployment pattern
- Building a foundation before adding complexity

## Architecture

## What's Included

This Terraform configuration creates:

- **S3 Bucket**: Stores agent source code for version-controlled builds
- **ECR Repository**: Container registry for the agent Docker image
- **CodeBuild Project**: Automated Docker image building and pushing
- **IAM Roles**: Execution roles for the agent and CodeBuild
- **AgentCore Runtime**: Serverless agent runtime with the deployed container

### Agent Code Management

The `agent-code/` directory contains your agent's source files:

- `basic_agent.py` - Agent implementation
- `Dockerfile` - Container configuration
- `requirements.txt` - Python dependencies

**Automatic Change Detection**:

- Terraform archives the `agent-code/` directory
- Uploads to S3 with MD5-based versioning
- CodeBuild pulls from S3 and builds the Docker image
- Any changes to files trigger automatic rebuild (new files, modifications, deletions)

## Prerequisites

### Required Tools

1. **Terraform** (>= 1.6)
1. **Recommended**: [tfenv](https://github.com/tfutils/tfenv) for version management
1. **Or download directly**: [terraform.io/downloads](https://www.terraform.io/downloads)

**Note**: `brew install terraform` provides v1.5.7 (deprecated). Use tfenv or direct download for >= 1.6.

1. **AWS CLI** (configured with credentials)

   ```
   aws configure
   ```

1. **Python 3.11+** (for testing scripts)

   ```
   python --version  # Verify Python 3.11 or later
   pip install boto3
   ```

1. **Docker** (for local testing, optional)

### AWS Account Requirements

- AWS Account with appropriate permissions
- Access to Amazon Bedrock models

## Quick Start

### 1. Configure Variables

Copy the example variables file and customize:

```
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your preferred values.

### 2. Initialize Terraform

See [State Management Options](https://aws.github.io/https:/raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/README.md#state-management-options) in the main README for detailed guidance on local vs. remote state.

**Quick start with local state:**

```
terraform init
```

**For team collaboration, use remote state** - see the [main README](https://aws.github.io/https:/raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/README.md#state-management-options) for setup instructions.

### 3. Review the Plan

```
terraform plan
```

### 4. Deploy

**Method 1: Using Deploy Script (Recommended)**

Make the script executable (first-time only):

```
chmod +x deploy.sh
```

Then deploy:

```
./deploy.sh
```

The deploy script:

- Validates Terraform configuration
- Shows deployment plan
- Prompts for confirmation
- Applies changes

**Method 2: Direct Terraform Commands**

```
terraform apply
```

When prompted, type `yes` to confirm the deployment.

**Note**: The deployment process includes:

1. Creating ECR repository
1. Building Docker image via CodeBuild
1. Creating AgentCore Runtime

Total deployment time: **~3-5 minutes**

### 5. Get Outputs

After deployment completes:

```
terraform output
```

Example output:

```
agent_runtime_id = "AGENT1234567890"
agent_runtime_arn = "arn:aws:bedrock-agentcore:<us-west-2>:123456789012:agent-runtime/AGENT1234567890"
ecr_repository_url = "123456789012.dkr.ecr.us-west-2.amazonaws.com/agentcore-basic-basic-agent"
```

## Testing the Agent

### Prerequisites for Testing

Before testing, ensure you have the required packages installed:

**Option A: Using uv (Recommended)**

```
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install boto3  # Required for agent invocation
```

**Option B: System-wide installation**

```
pip install boto3  # Required for agent invocation
```

**Note**: `boto3` is required for the test script to invoke the agent runtime via AWS API.

### Option 1: Using Test Script (Recommended)

```
# Run the test suite
python test_basic_agent.py $(terraform output -raw agent_runtime_arn)
```

### Option 2: Using AWS CLI

```
# Get the runtime ARN from outputs
RUNTIME_ARN=$(terraform output -raw agent_runtime_arn)

# Invoke the agent
aws bedrock-agentcore invoke-agent-runtime \
  --agent-runtime-arn $RUNTIME_ARN \
  --qualifier DEFAULT \
  --payload $(echo '{"prompt": "Hello, introduce yourself"}' | base64) \
  response.json

# View the response
cat response.json | jq -r '.response'
```

### Option 3: Using AWS Console

1. Navigate to Amazon Bedrock console
1. Go to AgentCore → Runtimes
1. Select your runtime
1. Use the "Test" feature to send queries

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

## Customization

### Modify Agent Code

Edit files in `agent-code/` and deploy:

- `basic_agent.py` - Agent logic and system prompt
- `Dockerfile` - Container configuration
- `requirements.txt` - Python dependencies

Changes are automatically detected and trigger rebuild. Run `terraform apply` to deploy.

### Environment Variables

Add to `terraform.tfvars`:

```
environment_variables = {
  LOG_LEVEL = "DEBUG"
}
```

### Network Mode

Set `network_mode = "PRIVATE"` for VPC deployment (requires additional VPC configuration).

## File Structure

```
basic-runtime/
├── main.tf                      # AgentCore runtime resource
├── variables.tf                 # Input variables
├── outputs.tf                   # Output values
├── versions.tf                  # Provider configuration
├── iam.tf                       # IAM roles and policies
├── s3.tf                        # S3 bucket for source code
├── ecr.tf                       # ECR repository
├── codebuild.tf                 # Docker build automation
├── buildspec.yml                # CodeBuild build specification
├── terraform.tfvars.example     # Example configuration
├── backend.tf.example           # Remote state example
├── test_basic_agent.py          # Automated test script
├── agent-code/                  # Agent source code
│   ├── basic_agent.py          # Agent implementation
│   ├── Dockerfile              # Container configuration
│   └── requirements.txt        # Python dependencies
├── scripts/                     # Build automation scripts
│   └── build-image.sh          # CodeBuild trigger & verification
├── deploy.sh                    # Deployment helper script
├── destroy.sh                   # Cleanup helper script
├── .gitignore                   # Git ignore patterns
└── README.md                    # This file
```

## Troubleshooting

### CodeBuild Fails

If the Docker build fails:

1. Check CodeBuild logs:

   ```
   aws codebuild batch-get-builds \
     --ids $(terraform output -raw codebuild_project_name) \
     --region us-west-2
   ```

1. Common issues:

1. Network connectivity issues

1. ECR authentication problems

1. Python dependency conflicts

### Runtime Creation Fails

If the runtime creation fails:

1. Verify the Docker image exists:

   ```
   aws ecr describe-images \
     --repository-name $(terraform output -raw ecr_repository_url | cut -d'/' -f2) \
     --region us-west-2
   ```

1. Check IAM role permissions

1. Verify Bedrock AgentCore service quotas

### Agent Invocation Fails

If invoking the agent fails:

1. Check runtime status in AWS Console
1. Review CloudWatch Logs for the runtime
1. Verify Bedrock model access permissions

## Cleanup

### Destroy All Resources

Make the script executable (first-time only):

```
chmod +x destroy.sh
```

Then cleanup:

```
./destroy.sh
```

Or use Terraform directly:

```
terraform destroy
```

### Verify Cleanup

Confirm all resources are deleted:

```
# Check ECR repositories
aws ecr describe-repositories --region us-west-2 | grep agentcore-basic

# Check AgentCore runtimes
aws bedrock-agentcore list-agent-runtimes --region us-west-2
```

## Pricing

For current pricing information, please refer to:

- [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [Amazon ECR Pricing](https://aws.amazon.com/ecr/pricing/)
- [AWS CodeBuild Pricing](https://aws.amazon.com/codebuild/pricing/)
- [Amazon S3 Pricing](https://aws.amazon.com/s3/pricing/)
- [Amazon CloudWatch Pricing](https://aws.amazon.com/cloudwatch/pricing/)

**Note**: Actual costs depend on your usage patterns, AWS region, and specific services consumed.

## Next Steps

### Explore Other Patterns

- [MCP Server Runtime](https://aws.github.io/https:/raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/mcp-server-agentcore-runtime/index.md) - Add MCP protocol support
- [Multi-Agent Runtime](https://aws.github.io/https:/raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/multi-agent-runtime/index.md) - Deploy multiple coordinating agents
- [End-to-End Weather Agent](https://aws.github.io/https:/raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/04-infrastructure-as-code/terraform/end-to-end-weather-agent/index.md) - Full-featured agent with tools

## Resources

- [Terraform AWS Provider Documentation](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore.html)
- [Strands Agents Documentation](https://strands-agents.readthedocs.io/)
- [AgentCore Samples Repository](https://github.com/aws-samples/amazon-bedrock-agentcore-samples)

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](https://aws.github.io/https:/raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://aws.github.io/https:/raw.githubusercontent.com/awslabs/amazon-bedrock-agentcore-samples/refs/heads/main/LICENSE) file for details.
