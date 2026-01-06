### main.tf

```
# ============================================================================
# AgentCore Runtime - Main Agent Runtime Resource
# ============================================================================

resource "aws_bedrockagentcore_agent_runtime" "basic_agent" {
  agent_runtime_name = replace("${var.stack_name}_${var.agent_name}", "-", "_")
  description        = var.description
  role_arn           = aws_iam_role.agent_execution.arn

  agent_runtime_artifact {
    container_configuration {
      container_uri = "${aws_ecr_repository.agent_ecr.repository_url}:${var.image_tag}"
    }
  }

  network_configuration {
    network_mode = var.network_mode
  }

  environment_variables = merge(
    {
      AWS_REGION         = var.aws_region
      AWS_DEFAULT_REGION = var.aws_region
    },
    var.environment_variables
  )

  depends_on = [
    null_resource.trigger_build,
    aws_iam_role_policy.agent_execution,
    aws_iam_role_policy_attachment.agent_execution_managed
  ]
}
```

### variables.tf

```
variable "agent_name" {
  description = "Name for the agent runtime"
  type        = string
  default     = "BasicAgent"

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]{0,47}$", var.agent_name))
    error_message = "Agent name must start with a letter, max 48 characters, alphanumeric and underscores only."
  }
}

variable "network_mode" {
  description = "Network mode for AgentCore resources"
  type        = string
  default     = "PUBLIC"

  validation {
    condition     = contains(["PUBLIC", "PRIVATE"], var.network_mode)
    error_message = "Network mode must be either PUBLIC or PRIVATE."
  }
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}

variable "aws_region" {
  description = "AWS region for deployment (REQUIRED)"
  type        = string
  # No default - must be explicitly provided

  validation {
    condition     = can(regex("^[a-z]{2}-[a-z]+-\\d{1}$", var.aws_region))
    error_message = "Must be a valid AWS region (e.g., us-east-1, eu-west-1)"
  }
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "stack_name" {
  description = "Stack name for resource naming"
  type        = string
  default     = "agentcore-basic"
}

variable "description" {
  description = "Description of the agent runtime"
  type        = string
  default     = "Basic agent runtime without memory, code interpreter, or browser"
}

variable "environment_variables" {
  description = "Environment variables for the agent runtime"
  type        = map(string)
  default     = {}
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
  default     = "basic-agent"
}
```

### outputs.tf

```
output "agent_runtime_id" {
  description = "ID of the created agent runtime"
  value       = aws_bedrockagentcore_agent_runtime.basic_agent.agent_runtime_id
}

output "agent_runtime_arn" {
  description = "ARN of the created agent runtime"
  value       = aws_bedrockagentcore_agent_runtime.basic_agent.agent_runtime_arn
}

output "agent_runtime_version" {
  description = "Version of the created agent runtime"
  value       = aws_bedrockagentcore_agent_runtime.basic_agent.agent_runtime_version
}

output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.agent_ecr.repository_url
}

output "ecr_repository_arn" {
  description = "ARN of the ECR repository"
  value       = aws_ecr_repository.agent_ecr.arn
}

output "agent_execution_role_arn" {
  description = "ARN of the agent execution role"
  value       = aws_iam_role.agent_execution.arn
}

output "codebuild_project_name" {
  description = "Name of the CodeBuild project"
  value       = aws_codebuild_project.agent_image.name
}

output "codebuild_project_arn" {
  description = "ARN of the CodeBuild project"
  value       = aws_codebuild_project.agent_image.arn
}

output "source_bucket_name" {
  description = "S3 bucket containing agent source code"
  value       = aws_s3_bucket.agent_source.id
}

output "source_bucket_arn" {
  description = "ARN of the S3 bucket containing agent source code"
  value       = aws_s3_bucket.agent_source.arn
}

output "source_object_key" {
  description = "S3 object key for the agent source code archive"
  value       = aws_s3_object.agent_source.key
}

output "source_code_md5" {
  description = "MD5 hash of the agent source code (triggers rebuild when changed)"
  value       = data.archive_file.agent_source.output_md5
}
```

### versions.tf

```
terraform {
  required_version = ">= 1.6"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.21"
    }
    null = {
      source  = "hashicorp/null"
      version = "~> 3.0"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.9"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "AgentCore"
      Pattern     = "basic-runtime"
      Environment = var.environment
      StackName   = var.stack_name
      ManagedBy   = "Terraform"
    }
  }
}
```

### iam.tf

```
# Data sources
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ============================================================================
# Agent Execution Role - For AgentCore Runtime
# ============================================================================

resource "aws_iam_role" "agent_execution" {
  name = "${var.stack_name}-agent-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid    = "AssumeRolePolicy"
      Effect = "Allow"
      Principal = {
        Service = "bedrock-agentcore.amazonaws.com"
      }
      Action = "sts:AssumeRole"
      Condition = {
        StringEquals = {
          "aws:SourceAccount" = data.aws_caller_identity.current.id
        }
        ArnLike = {
          "aws:SourceArn" = "arn:aws:bedrock-agentcore:${data.aws_region.current.id}:${data.aws_caller_identity.current.id}:*"
        }
      }
    }]
  })

  tags = {
    Name   = "${var.stack_name}-agent-execution-role"
    Module = "IAM"
  }
}

# Attach AWS managed policy for AgentCore
resource "aws_iam_role_policy_attachment" "agent_execution_managed" {
  role       = aws_iam_role.agent_execution.name
  policy_arn = "arn:aws:iam::aws:policy/BedrockAgentCoreFullAccess"
}

# Inline policy for agent execution
resource "aws_iam_role_policy" "agent_execution" {
  name = "AgentCoreExecutionPolicy"
  role = aws_iam_role.agent_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ECR Access
      {
        Sid    = "ECRImageAccess"
        Effect = "Allow"
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchCheckLayerAvailability"
        ]
        Resource = aws_ecr_repository.agent_ecr.arn
      },
      {
        Sid      = "ECRTokenAccess"
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      # CloudWatch Logs
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:DescribeLogStreams",
          "logs:CreateLogGroup",
          "logs:DescribeLogGroups",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.id}:${data.aws_caller_identity.current.id}:log-group:/aws/bedrock-agentcore/runtimes/*"
      },
      # X-Ray Tracing
      {
        Sid    = "XRayTracing"
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets"
        ]
        Resource = "*"
      },
      # CloudWatch Metrics
      {
        Sid      = "CloudWatchMetrics"
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData"]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "bedrock-agentcore"
          }
        }
      },
      # Bedrock Model Invocation
      {
        Sid    = "BedrockModelInvocation"
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = "*"
      },
      # Workload Access Tokens
      {
        Sid    = "GetAgentAccessToken"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:GetWorkloadAccessToken",
          "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
          "bedrock-agentcore:GetWorkloadAccessTokenForUserId"
        ]
        Resource = [
          "arn:aws:bedrock-agentcore:${data.aws_region.current.id}:${data.aws_caller_identity.current.id}:workload-identity-directory/default",
          "arn:aws:bedrock-agentcore:${data.aws_region.current.id}:${data.aws_caller_identity.current.id}:workload-identity-directory/default/workload-identity/*"
        ]
      }
    ]
  })
}

# ============================================================================
# CodeBuild Service Role - For Docker Image Building
# ============================================================================

resource "aws_iam_role" "image_build" {
  name = "${var.stack_name}-codebuild-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "codebuild.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })

  tags = {
    Name   = "${var.stack_name}-codebuild-role"
    Module = "IAM"
  }
}

# Inline policy for CodeBuild
resource "aws_iam_role_policy" "image_build" {
  name = "CodeBuildPolicy"
  role = aws_iam_role.image_build.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # CloudWatch Logs
      {
        Sid    = "CloudWatchLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${data.aws_region.current.id}:${data.aws_caller_identity.current.id}:log-group:/aws/codebuild/*"
      },
      # ECR Access
      {
        Sid    = "ECRAccess"
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:GetAuthorizationToken",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = [
          aws_ecr_repository.agent_ecr.arn,
          "*"
        ]
      },
      # S3 Source Access (for agent-code)
      {
        Sid    = "S3SourceAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = "${aws_s3_bucket.agent_source.arn}/*"
      },
      {
        Sid    = "S3BucketAccess"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = aws_s3_bucket.agent_source.arn
      }
    ]
  })
}
```

### s3.tf

```
# ============================================================================
# S3 Bucket for Agent Source Code (CDK Asset Equivalent)
# ============================================================================

resource "aws_s3_bucket" "agent_source" {
  bucket_prefix = "${var.stack_name}-agent-source-"
  force_destroy = true

  tags = {
    Name    = "${var.stack_name}-agent-source"
    Purpose = "Store agent source code for CodeBuild"
  }
}

# Block public access
resource "aws_s3_bucket_public_access_block" "agent_source" {
  bucket = aws_s3_bucket.agent_source.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning for source code tracking
resource "aws_s3_bucket_versioning" "agent_source" {
  bucket = aws_s3_bucket.agent_source.id

  versioning_configuration {
    status = "Enabled"
  }
}

# ============================================================================
# Archive and Upload Agent Source Code
# ============================================================================

# Archive agent-code/ directory
# This automatically detects ALL files including new ones
data "archive_file" "agent_source" {
  type        = "zip"
  source_dir  = "${path.module}/agent-code"
  output_path = "${path.module}/.terraform/agent-code.zip"
}

# Upload to S3 (re-uploads when MD5 changes)
resource "aws_s3_object" "agent_source" {
  bucket = aws_s3_bucket.agent_source.id
  key    = "agent-code-${data.archive_file.agent_source.output_md5}.zip"
  source = data.archive_file.agent_source.output_path
  etag   = data.archive_file.agent_source.output_md5

  tags = {
    Name      = "agent-source-code"
    MD5       = data.archive_file.agent_source.output_md5
    Timestamp = timestamp()
  }
}
```

### ecr.tf

```
# ============================================================================
# ECR Repository - Container Registry for Agent Image
# ============================================================================

resource "aws_ecr_repository" "agent_ecr" {
  name                 = "${var.stack_name}-${var.ecr_repository_name}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  force_delete = true

  tags = {
    Name   = "${var.stack_name}-ecr-repository"
    Module = "ECR"
  }
}

# ECR Repository Policy
resource "aws_ecr_repository_policy" "agent_ecr" {
  repository = aws_ecr_repository.agent_ecr.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowPullFromAccount"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.id}:root"
        }
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer"
        ]
      }
    ]
  })
}

# ECR Lifecycle Policy - Keep last 5 images
resource "aws_ecr_lifecycle_policy" "agent_ecr" {
  repository = aws_ecr_repository.agent_ecr.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 5 images"
        selection = {
          tagStatus   = "any"
          countType   = "imageCountMoreThan"
          countNumber = 5
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
```

### codebuild.tf

```
# ============================================================================
# CodeBuild Project - Build and Push Docker Image
# ============================================================================

resource "aws_codebuild_project" "agent_image" {
  name          = "${var.stack_name}-basic-agent-build"
  description   = "Build basic agent Docker image for ${var.stack_name}"
  service_role  = aws_iam_role.image_build.arn
  build_timeout = 60

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    compute_type                = "BUILD_GENERAL1_LARGE"
    image                       = "aws/codebuild/amazonlinux2-aarch64-standard:3.0"
    type                        = "ARM_CONTAINER"
    privileged_mode             = true
    image_pull_credentials_type = "CODEBUILD"

    environment_variable {
      name  = "AWS_DEFAULT_REGION"
      value = data.aws_region.current.id
    }

    environment_variable {
      name  = "AWS_ACCOUNT_ID"
      value = data.aws_caller_identity.current.id
    }

    environment_variable {
      name  = "IMAGE_REPO_NAME"
      value = aws_ecr_repository.agent_ecr.name
    }

    environment_variable {
      name  = "IMAGE_TAG"
      value = var.image_tag
    }

    environment_variable {
      name  = "STACK_NAME"
      value = var.stack_name
    }
  }

  source {
    type      = "S3"
    location  = "${aws_s3_bucket.agent_source.id}/${aws_s3_object.agent_source.key}"
    buildspec = file("${path.module}/buildspec.yml")
  }

  logs_config {
    cloudwatch_logs {
      group_name = "/aws/codebuild/${var.stack_name}-basic-agent-build"
    }
  }

  tags = {
    Name   = "${var.stack_name}-basic-build"
    Module = "CodeBuild"
  }
}

# ============================================================================
# Trigger CodeBuild - Build Image Before Creating Runtime
# ============================================================================

resource "null_resource" "trigger_build" {
  triggers = {
    build_project = aws_codebuild_project.agent_image.id
    image_tag     = var.image_tag
    # Trigger rebuild if ECR repository changes
    ecr_repository = aws_ecr_repository.agent_ecr.id
    # Trigger rebuild when source code changes (MD5 hash)
    source_code_md5 = data.archive_file.agent_source.output_md5
  }

  provisioner "local-exec" {
    command = "${path.module}/scripts/build-image.sh \"${aws_codebuild_project.agent_image.name}\" \"${data.aws_region.current.id}\" \"${aws_ecr_repository.agent_ecr.name}\" \"${var.image_tag}\" \"${aws_ecr_repository.agent_ecr.repository_url}\""
  }

  depends_on = [
    aws_codebuild_project.agent_image,
    aws_ecr_repository.agent_ecr,
    aws_iam_role_policy.image_build,
    aws_s3_object.agent_source
  ]
}
```

### buildspec.yml

```
version: 0.2

phases:
  install:
    commands:
      - echo Installing dependencies...
      - yum install -y unzip

  pre_build:
    commands:
      - echo Source code already extracted by CodeBuild...
      - cd $CODEBUILD_SRC_DIR
      - ls -la
      - echo Logging in to Amazon ECR...
      - aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com

  build:
    commands:
      - echo Build started on `date`
      - echo Building the Docker image for basic agent ARM64 from agent-code/...
      - docker build -t $IMAGE_REPO_NAME:$IMAGE_TAG .
      - docker tag $IMAGE_REPO_NAME:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG

  post_build:
    commands:
      - echo Build completed on `date`
      - echo Pushing the Docker image...
      - docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG
      - echo ARM64 Docker image pushed successfully
```

### terraform.tfvars.example

```
# ============================================================================
# Basic AgentCore Runtime - Example Configuration
# ============================================================================
# Copy this file to terraform.tfvars and customize the values
# Example: cp terraform.tfvars.example terraform.tfvars

# Agent Configuration
agent_name  = "BasicAgent"
stack_name  = "agentcore-basic"
description = "Basic agent runtime without memory, code interpreter, or browser"

# Network Configuration
network_mode = "PUBLIC" # Options: PUBLIC, PRIVATE

# Container Configuration
ecr_repository_name = "basic-agent"
image_tag           = "latest"

# AWS Configuration
aws_region  = "us-west-2"
environment = "dev"

# Optional: Environment Variables for the Agent Runtime
# environment_variables = {
#   LOG_LEVEL = "INFO"
#   CUSTOM_VAR = "value"
# }
```

### agent-code/Dockerfile

```
FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir aws-opentelemetry-distro==0.10.1

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 8080
EXPOSE 8000

COPY . .

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8080/ping || exit 1

CMD ["opentelemetry-instrument", "python", "-m", "basic_agent"]
```

### agent-code/basic_agent.py

```
from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

def create_basic_agent() -> Agent:
    """Create a basic agent with simple functionality"""
    system_prompt = """You are a helpful assistant. Answer questions clearly and concisely."""

    return Agent(
        system_prompt=system_prompt,
        name="BasicAgent"
    )

@app.entrypoint
async def invoke(payload=None):
    """Main entrypoint for the agent"""
    try:
        # Get the query from payload
        query = payload.get("prompt", "Hello, how are you?") if payload else "Hello, how are you?"

        # Create and use the agent
        agent = create_basic_agent()
        response = agent(query)

        return {
            "status": "success",
            "response": response.message['content'][0]['text']
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    app.run()
```

### agent-code/requirements.txt

```
strands-agents
boto3
bedrock-agentcore
```
