### main.tf

```
# ============================================================================
# Wait for IAM propagation before triggering builds
# ============================================================================

resource "time_sleep" "wait_for_iam" {
  depends_on = [
    aws_iam_role_policy.codebuild,
    aws_iam_role_policy.orchestrator_execution,
    aws_iam_role_policy.specialist_execution
  ]

  create_duration = "30s"
}

# ============================================================================
# Trigger CodeBuild - Sequential Build Process
# Specialist builds first (independent), then Orchestrator (depends on Specialist)
# ============================================================================

# Trigger Specialist Build (Independent - Builds First)
resource "null_resource" "trigger_build_specialist" {
  triggers = {
    build_project   = aws_codebuild_project.specialist_image.id
    image_tag       = var.image_tag
    ecr_repository  = aws_ecr_repository.specialist.id
    source_code_md5 = data.archive_file.specialist_source.output_md5
  }

  provisioner "local-exec" {
    command = "${path.module}/scripts/build-image.sh \"${aws_codebuild_project.specialist_image.name}\" \"${data.aws_region.current.id}\" \"${aws_ecr_repository.specialist.name}\" \"${var.image_tag}\" \"${aws_ecr_repository.specialist.repository_url}\""
  }

  depends_on = [
    aws_codebuild_project.specialist_image,
    aws_ecr_repository.specialist,
    aws_iam_role_policy.codebuild,
    aws_s3_object.specialist_source,
    time_sleep.wait_for_iam
  ]
}

# Trigger Orchestrator Build (Depends on Specialist Build Completion)
resource "null_resource" "trigger_build_orchestrator" {
  triggers = {
    build_project   = aws_codebuild_project.orchestrator_image.id
    image_tag       = var.image_tag
    ecr_repository  = aws_ecr_repository.orchestrator.id
    source_code_md5 = data.archive_file.orchestrator_source.output_md5
    # Also rebuild if Specialist build changes
    specialist_build = null_resource.trigger_build_specialist.id
  }

  provisioner "local-exec" {
    command = "${path.module}/scripts/build-image.sh \"${aws_codebuild_project.orchestrator_image.name}\" \"${data.aws_region.current.id}\" \"${aws_ecr_repository.orchestrator.name}\" \"${var.image_tag}\" \"${aws_ecr_repository.orchestrator.repository_url}\""
  }

  depends_on = [
    aws_codebuild_project.orchestrator_image,
    aws_ecr_repository.orchestrator,
    aws_iam_role_policy.codebuild,
    aws_s3_object.orchestrator_source,
    null_resource.trigger_build_specialist, # CRITICAL: Wait for Specialist build
    time_sleep.wait_for_iam
  ]
}
```

### variables.tf

```
variable "orchestrator_name" {
  description = "Name for the orchestrator agent runtime"
  type        = string
  default     = "OrchestratorAgent"

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]{0,47}$", var.orchestrator_name))
    error_message = "Agent name must start with a letter, max 48 characters, alphanumeric and underscores only."
  }
}

variable "specialist_name" {
  description = "Name for the specialist agent runtime"
  type        = string
  default     = "SpecialistAgent"

  validation {
    condition     = can(regex("^[a-zA-Z][a-zA-Z0-9_]{0,47}$", var.specialist_name))
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
  default     = "agentcore-multi-agent"
}

variable "environment_variables" {
  description = "Environment variables for the agent runtime"
  type        = map(string)
  default     = {}
}

variable "ecr_repository_name" {
  description = "Base name of the ECR repositories"
  type        = string
  default     = "multi-agent"
}
```

### outputs.tf

```
# ============================================================================
# Orchestrator Agent Outputs
# ============================================================================

output "orchestrator_runtime_id" {
  description = "ID of orchestrator agent runtime"
  value       = aws_bedrockagentcore_agent_runtime.orchestrator.agent_runtime_id
}

output "orchestrator_runtime_arn" {
  description = "ARN of orchestrator agent runtime"
  value       = aws_bedrockagentcore_agent_runtime.orchestrator.agent_runtime_arn
}

output "orchestrator_runtime_version" {
  description = "Version of orchestrator agent runtime"
  value       = aws_bedrockagentcore_agent_runtime.orchestrator.agent_runtime_version
}

output "orchestrator_ecr_repository_url" {
  description = "URL of the ECR repository for orchestrator agent"
  value       = aws_ecr_repository.orchestrator.repository_url
}

output "orchestrator_execution_role_arn" {
  description = "ARN of the orchestrator agent execution role"
  value       = aws_iam_role.orchestrator_execution.arn
}

# ============================================================================
# Specialist Agent Outputs
# ============================================================================

output "specialist_runtime_id" {
  description = "ID of specialist agent runtime"
  value       = aws_bedrockagentcore_agent_runtime.specialist.agent_runtime_id
}

output "specialist_runtime_arn" {
  description = "ARN of specialist agent runtime"
  value       = aws_bedrockagentcore_agent_runtime.specialist.agent_runtime_arn
}

output "specialist_runtime_version" {
  description = "Version of specialist agent runtime"
  value       = aws_bedrockagentcore_agent_runtime.specialist.agent_runtime_version
}

output "specialist_ecr_repository_url" {
  description = "URL of the ECR repository for specialist agent"
  value       = aws_ecr_repository.specialist.repository_url
}

output "specialist_execution_role_arn" {
  description = "ARN of the specialist agent execution role"
  value       = aws_iam_role.specialist_execution.arn
}

# ============================================================================
# Build & Storage Outputs
# ============================================================================

output "orchestrator_codebuild_project_name" {
  description = "Name of the CodeBuild project for orchestrator agent"
  value       = aws_codebuild_project.orchestrator_image.name
}

output "specialist_codebuild_project_name" {
  description = "Name of the CodeBuild project for specialist agent"
  value       = aws_codebuild_project.specialist_image.name
}

output "orchestrator_source_bucket_name" {
  description = "S3 bucket containing orchestrator agent source code"
  value       = aws_s3_bucket.orchestrator_source.id
}

output "specialist_source_bucket_name" {
  description = "S3 bucket containing specialist agent source code"
  value       = aws_s3_bucket.specialist_source.id
}

output "orchestrator_source_code_md5" {
  description = "MD5 hash of orchestrator source code (triggers rebuild when changed)"
  value       = data.archive_file.orchestrator_source.output_md5
}

output "specialist_source_code_md5" {
  description = "MD5 hash of specialist source code (triggers rebuild when changed)"
  value       = data.archive_file.specialist_source.output_md5
}

# ============================================================================
# Testing Information
# ============================================================================

output "test_orchestrator_command" {
  description = "AWS CLI command to test orchestrator agent"
  value       = "aws bedrock-agentcore invoke-agent-runtime --agent-runtime-id ${aws_bedrockagentcore_agent_runtime.orchestrator.agent_runtime_id} --qualifier DEFAULT --payload '{\"prompt\": \"Hello, how are you?\"}' --region ${data.aws_region.current.id} response.json"
}

output "test_specialist_command" {
  description = "AWS CLI command to test specialist agent"
  value       = "aws bedrock-agentcore invoke-agent-runtime --agent-runtime-id ${aws_bedrockagentcore_agent_runtime.specialist.agent_runtime_id} --qualifier DEFAULT --payload '{\"prompt\": \"Explain cloud computing\"}' --region ${data.aws_region.current.id} response.json"
}

output "test_script_command" {
  description = "Command to test multi-agent communication"
  value       = "python test_multi_agent.py ${aws_bedrockagentcore_agent_runtime.orchestrator.agent_runtime_arn}"
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
      Pattern     = "multi-agent-runtime"
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
# Orchestrator Agent Execution Role - For AgentCore Runtime
# ============================================================================

resource "aws_iam_role" "orchestrator_execution" {
  name = "${var.stack_name}-orchestrator-execution-role"

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
    Name   = "${var.stack_name}-orchestrator-execution-role"
    Module = "IAM"
    Agent  = "Orchestrator"
  }
}

# Attach AWS managed policy for AgentCore - Orchestrator
resource "aws_iam_role_policy_attachment" "orchestrator_execution_managed" {
  role       = aws_iam_role.orchestrator_execution.name
  policy_arn = "arn:aws:iam::aws:policy/BedrockAgentCoreFullAccess"
}

# Inline policy for orchestrator execution
resource "aws_iam_role_policy" "orchestrator_execution" {
  name = "OrchestratorCoreExecutionPolicy"
  role = aws_iam_role.orchestrator_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ECR Access for Orchestrator
      {
        Sid    = "ECRImageAccess"
        Effect = "Allow"
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchCheckLayerAvailability"
        ]
        Resource = aws_ecr_repository.orchestrator.arn
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
# Orchestrator A2A Policy - Allows Orchestrator to Invoke Specialist
# ============================================================================

resource "aws_iam_role_policy" "orchestrator_invoke_specialist" {
  name = "OrchestratorInvokeSpecialistPolicy"
  role = aws_iam_role.orchestrator_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "InvokeSpecialistRuntime"
        Effect = "Allow"
        Action = [
          "bedrock-agentcore:InvokeAgentRuntime"
        ]
        Resource = "arn:aws:bedrock-agentcore:${data.aws_region.current.id}:${data.aws_caller_identity.current.id}:runtime/*"
      }
    ]
  })
}

# ============================================================================
# Specialist Agent Execution Role - For AgentCore Runtime
# ============================================================================

resource "aws_iam_role" "specialist_execution" {
  name = "${var.stack_name}-specialist-execution-role"

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
    Name   = "${var.stack_name}-specialist-execution-role"
    Module = "IAM"
    Agent  = "Specialist"
  }
}

# Attach AWS managed policy for AgentCore - Specialist
resource "aws_iam_role_policy_attachment" "specialist_execution_managed" {
  role       = aws_iam_role.specialist_execution.name
  policy_arn = "arn:aws:iam::aws:policy/BedrockAgentCoreFullAccess"
}

# Inline policy for specialist execution
resource "aws_iam_role_policy" "specialist_execution" {
  name = "SpecialistCoreExecutionPolicy"
  role = aws_iam_role.specialist_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ECR Access for Specialist
      {
        Sid    = "ECRImageAccess"
        Effect = "Allow"
        Action = [
          "ecr:BatchGetImage",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchCheckLayerAvailability"
        ]
        Resource = aws_ecr_repository.specialist.arn
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
# CodeBuild Service Role - For Docker Image Building (Both Agents)
# ============================================================================

resource "aws_iam_role" "codebuild" {
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
resource "aws_iam_role_policy" "codebuild" {
  name = "CodeBuildPolicy"
  role = aws_iam_role.codebuild.id

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
      # ECR Access for both repositories
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
          aws_ecr_repository.orchestrator.arn,
          aws_ecr_repository.specialist.arn,
          "*"
        ]
      },
      # S3 Source Access for both agent code buckets
      {
        Sid    = "S3SourceAccess"
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:GetObjectVersion"
        ]
        Resource = [
          "${aws_s3_bucket.orchestrator_source.arn}/*",
          "${aws_s3_bucket.specialist_source.arn}/*"
        ]
      },
      {
        Sid    = "S3BucketAccess"
        Effect = "Allow"
        Action = [
          "s3:ListBucket",
          "s3:GetBucketLocation"
        ]
        Resource = [
          aws_s3_bucket.orchestrator_source.arn,
          aws_s3_bucket.specialist_source.arn
        ]
      }
    ]
  })
}
```

### s3.tf

```
# ============================================================================
# S3 Buckets for Agent Source Code (CDK Asset Equivalent)
# ============================================================================

# Orchestrator Agent Source Bucket
resource "aws_s3_bucket" "orchestrator_source" {
  bucket_prefix = "acma-orch-src-" # Shortened to fit 37 char limit
  force_destroy = true

  tags = {
    Name    = "${var.stack_name}-orchestrator-source"
    Purpose = "Store Orchestrator agent source code for CodeBuild"
  }
}

# Specialist Agent Source Bucket
resource "aws_s3_bucket" "specialist_source" {
  bucket_prefix = "acma-spec-src-" # Shortened to fit 37 char limit
  force_destroy = true

  tags = {
    Name    = "${var.stack_name}-specialist-source"
    Purpose = "Store Specialist agent source code for CodeBuild"
  }
}

# Block public access - Orchestrator
resource "aws_s3_bucket_public_access_block" "orchestrator_source" {
  bucket = aws_s3_bucket.orchestrator_source.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Block public access - Specialist
resource "aws_s3_bucket_public_access_block" "specialist_source" {
  bucket = aws_s3_bucket.specialist_source.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable versioning - Orchestrator
resource "aws_s3_bucket_versioning" "orchestrator_source" {
  bucket = aws_s3_bucket.orchestrator_source.id

  versioning_configuration {
    status = "Enabled"
  }
}

# Enable versioning - Specialist
resource "aws_s3_bucket_versioning" "specialist_source" {
  bucket = aws_s3_bucket.specialist_source.id

  versioning_configuration {
    status = "Enabled"
  }
}

# ============================================================================
# Archive and Upload Agent Source Code
# ============================================================================

# Archive agent-orchestrator-code/ directory
data "archive_file" "orchestrator_source" {
  type        = "zip"
  source_dir  = "${path.module}/agent-orchestrator-code"
  output_path = "${path.module}/.terraform/agent-orchestrator-code.zip"
}

# Archive agent-specialist-code/ directory
data "archive_file" "specialist_source" {
  type        = "zip"
  source_dir  = "${path.module}/agent-specialist-code"
  output_path = "${path.module}/.terraform/agent-specialist-code.zip"
}

# Upload Orchestrator source to S3
resource "aws_s3_object" "orchestrator_source" {
  bucket = aws_s3_bucket.orchestrator_source.id
  key    = "agent-orchestrator-code-${data.archive_file.orchestrator_source.output_md5}.zip"
  source = data.archive_file.orchestrator_source.output_path
  etag   = data.archive_file.orchestrator_source.output_md5

  tags = {
    Name  = "agent-orchestrator-source-code"
    Agent = "Orchestrator"
    MD5   = data.archive_file.orchestrator_source.output_md5
  }
}

# Upload Specialist source to S3
resource "aws_s3_object" "specialist_source" {
  bucket = aws_s3_bucket.specialist_source.id
  key    = "agent-specialist-code-${data.archive_file.specialist_source.output_md5}.zip"
  source = data.archive_file.specialist_source.output_path
  etag   = data.archive_file.specialist_source.output_md5

  tags = {
    Name  = "agent-specialist-source-code"
    Agent = "Specialist"
    MD5   = data.archive_file.specialist_source.output_md5
  }
}
```

### ecr.tf

```
# ============================================================================
# ECR Repositories - Container Registries for Agent Images
# ============================================================================

# Orchestrator Agent ECR Repository
resource "aws_ecr_repository" "orchestrator" {
  name                 = "${var.stack_name}-${var.ecr_repository_name}-orchestrator"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  force_delete = true

  tags = {
    Name   = "${var.stack_name}-orchestrator-ecr-repository"
    Module = "ECR"
    Agent  = "Orchestrator"
  }
}

# Specialist Agent ECR Repository
resource "aws_ecr_repository" "specialist" {
  name                 = "${var.stack_name}-${var.ecr_repository_name}-specialist"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  force_delete = true

  tags = {
    Name   = "${var.stack_name}-specialist-ecr-repository"
    Module = "ECR"
    Agent  = "Specialist"
  }
}

# ECR Repository Policy - Orchestrator
resource "aws_ecr_repository_policy" "orchestrator" {
  repository = aws_ecr_repository.orchestrator.name

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

# ECR Repository Policy - Specialist
resource "aws_ecr_repository_policy" "specialist" {
  repository = aws_ecr_repository.specialist.name

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

# ECR Lifecycle Policy - Orchestrator - Keep last 5 images
resource "aws_ecr_lifecycle_policy" "orchestrator" {
  repository = aws_ecr_repository.orchestrator.name

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

# ECR Lifecycle Policy - Specialist - Keep last 5 images
resource "aws_ecr_lifecycle_policy" "specialist" {
  repository = aws_ecr_repository.specialist.name

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
# CodeBuild Project - Build and Push Orchestrator Agent Docker Image
# ============================================================================

resource "aws_codebuild_project" "orchestrator_image" {
  name          = "${var.stack_name}-orchestrator-build"
  description   = "Build Orchestrator agent Docker image for ${var.stack_name}"
  service_role  = aws_iam_role.codebuild.arn
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
      value = aws_ecr_repository.orchestrator.name
    }

    environment_variable {
      name  = "IMAGE_TAG"
      value = var.image_tag
    }

    environment_variable {
      name  = "STACK_NAME"
      value = var.stack_name
    }

    environment_variable {
      name  = "AGENT_NAME"
      value = "orchestrator"
    }
  }

  source {
    type      = "S3"
    location  = "${aws_s3_bucket.orchestrator_source.id}/${aws_s3_object.orchestrator_source.key}"
    buildspec = file("${path.module}/buildspec-orchestrator.yml")
  }

  logs_config {
    cloudwatch_logs {
      group_name = "/aws/codebuild/${var.stack_name}-orchestrator-build"
    }
  }

  tags = {
    Name   = "${var.stack_name}-orchestrator-build"
    Module = "CodeBuild"
    Agent  = "Orchestrator"
  }

  depends_on = [
    aws_iam_role_policy.codebuild
  ]
}

# ============================================================================
# CodeBuild Project - Build and Push Specialist Agent Docker Image
# ============================================================================

resource "aws_codebuild_project" "specialist_image" {
  name          = "${var.stack_name}-specialist-build"
  description   = "Build Specialist agent Docker image for ${var.stack_name}"
  service_role  = aws_iam_role.codebuild.arn
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
      value = aws_ecr_repository.specialist.name
    }

    environment_variable {
      name  = "IMAGE_TAG"
      value = var.image_tag
    }

    environment_variable {
      name  = "STACK_NAME"
      value = var.stack_name
    }

    environment_variable {
      name  = "AGENT_NAME"
      value = "specialist"
    }
  }

  source {
    type      = "S3"
    location  = "${aws_s3_bucket.specialist_source.id}/${aws_s3_object.specialist_source.key}"
    buildspec = file("${path.module}/buildspec-specialist.yml")
  }

  logs_config {
    cloudwatch_logs {
      group_name = "/aws/codebuild/${var.stack_name}-specialist-build"
    }
  }

  tags = {
    Name   = "${var.stack_name}-specialist-build"
    Module = "CodeBuild"
    Agent  = "Specialist"
  }

  depends_on = [
    aws_iam_role_policy.codebuild
  ]
}

# ============================================================================
# Note: Build triggers are defined in main.tf for proper sequencing
# Specialist builds first, then Orchestrator (which depends on Specialist ARN)
# ============================================================================
```

### orchestrator.tf

```
# ============================================================================
# Orchestrator Agent Runtime - Depends on Specialist Agent
# ============================================================================

resource "aws_bedrockagentcore_agent_runtime" "orchestrator" {
  agent_runtime_name = "${replace(var.stack_name, "-", "_")}_${var.orchestrator_name}"
  description        = "Orchestrator agent runtime for ${var.stack_name}"
  role_arn           = aws_iam_role.orchestrator_execution.arn

  agent_runtime_artifact {
    container_configuration {
      container_uri = "${aws_ecr_repository.orchestrator.repository_url}:${var.image_tag}"
    }
  }

  network_configuration {
    network_mode = var.network_mode
  }

  # CRITICAL: Specialist Agent ARN for A2A communication
  environment_variables = {
    AWS_REGION         = data.aws_region.current.id
    AWS_DEFAULT_REGION = data.aws_region.current.id
    SPECIALIST_ARN     = aws_bedrockagentcore_agent_runtime.specialist.agent_runtime_arn
  }

  tags = {
    Name        = "${var.stack_name}-orchestrator-runtime"
    Environment = "production"
    Module      = "BedrockAgentCore"
    Agent       = "Orchestrator"
  }

  # CRITICAL: Must wait for Specialist Agent to be created first
  depends_on = [
    aws_bedrockagentcore_agent_runtime.specialist,
    null_resource.trigger_build_orchestrator,
    aws_iam_role_policy.orchestrator_execution,
    aws_iam_role_policy.orchestrator_invoke_specialist,
    aws_iam_role_policy_attachment.orchestrator_execution_managed
  ]
}
```

### specialist.tf

```
# ============================================================================
# Specialist Agent Runtime - Independent Agent
# ============================================================================

resource "aws_bedrockagentcore_agent_runtime" "specialist" {
  agent_runtime_name = "${replace(var.stack_name, "-", "_")}_${var.specialist_name}"
  description        = "Specialist agent runtime for ${var.stack_name}"
  role_arn           = aws_iam_role.specialist_execution.arn

  agent_runtime_artifact {
    container_configuration {
      container_uri = "${aws_ecr_repository.specialist.repository_url}:${var.image_tag}"
    }
  }

  network_configuration {
    network_mode = var.network_mode
  }

  environment_variables = {
    AWS_REGION         = data.aws_region.current.id
    AWS_DEFAULT_REGION = data.aws_region.current.id
  }

  tags = {
    Name        = "${var.stack_name}-specialist-runtime"
    Environment = "production"
    Module      = "BedrockAgentCore"
    Agent       = "Specialist"
  }

  depends_on = [
    null_resource.trigger_build_specialist,
    aws_iam_role_policy.specialist_execution,
    aws_iam_role_policy_attachment.specialist_execution_managed
  ]
}
```

### buildspec-orchestrator.yml

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
      - echo Building the Docker image for Orchestrator Agent ARM64...
      - docker build -t $IMAGE_REPO_NAME:$IMAGE_TAG .
      - docker tag $IMAGE_REPO_NAME:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG

  post_build:
    commands:
      - echo Build completed on `date`
      - echo Pushing the Orchestrator Docker image...
      - docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG
      - echo Orchestrator Agent ARM64 Docker image pushed successfully
```

### buildspec-specialist.yml

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
      - echo Building the Docker image for Specialist Agent ARM64...
      - docker build -t $IMAGE_REPO_NAME:$IMAGE_TAG .
      - docker tag $IMAGE_REPO_NAME:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG

  post_build:
    commands:
      - echo Build completed on `date`
      - echo Pushing the Specialist Docker image...
      - docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG
      - echo Specialist Agent ARM64 Docker image pushed successfully
```

### terraform.tfvars.example

```
# ============================================================================
# Multi-Agent Runtime - Example Configuration
# ============================================================================
# Copy this file to terraform.tfvars and customize
# Example: cp terraform.tfvars.example terraform.tfvars

# Agent Configuration
orchestrator_name = "OrchestratorAgent"
specialist_name   = "SpecialistAgent"
stack_name        = "agentcore-multi-agent"

# Network Configuration
network_mode = "PUBLIC" # PUBLIC or PRIVATE

# Container Configuration
ecr_repository_name = "multi-agent"
image_tag           = "latest"

# AWS Configuration
aws_region  = "us-west-2"
environment = "dev"

# Optional: Environment Variables (if needed for custom configurations)
# environment_variables = {
#   LOG_LEVEL = "INFO"
# }

# Notes:
# - Orchestrator Agent: Receives user requests and delegates to Specialist
# - Specialist Agent: Provides specialized data processing capabilities
# - Orchestrator code in agent-orchestrator-code/ directory (includes A2A invocation logic)
# - Specialist code in agent-specialist-code/ directory (independent specialist)
# - A2A communication: Orchestrator can invoke Specialist via call_specialist_agent tool
# - Sequential deployment: Specialist builds first, then Orchestrator
# - Test with: python test_multi_agent.py
```

### agent-orchestrator-code/Dockerfile

```
FROM public.ecr.aws/docker/library/python:3.11-slim
WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip install aws-opentelemetry-distro>=0.10.1

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 8080
EXPOSE 8000

COPY . .

CMD ["opentelemetry-instrument", "python", "-m", "agent"]
```

### agent-orchestrator-code/agent.py

```
from strands import Agent, tool
from typing import Dict, Any
import boto3
import json
import os
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

# Environment variable for Specialist Agent ARN (required - set by Terraform)
SPECIALIST_ARN = os.getenv('SPECIALIST_ARN')
if not SPECIALIST_ARN:
    raise EnvironmentError("SPECIALIST_ARN environment variable is required")

def invoke_specialist(query: str) -> str:
    """Helper function to invoke specialist agent using boto3"""
    try:
        # Get region from environment (set by AgentCore runtime)
        region = os.getenv('AWS_REGION')
        if not region:
            raise EnvironmentError("AWS_REGION environment variable is required")
        agentcore_client = boto3.client('bedrock-agentcore', region_name=region)

        # Invoke specialist agent runtime (using AWS sample format)
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=SPECIALIST_ARN,
            qualifier="DEFAULT",
            payload=json.dumps({"prompt": query})
        )

        # Handle streaming response (text/event-stream)
        if "text/event-stream" in response.get("contentType", ""):
            result = ""
            for line in response["response"].iter_lines(chunk_size=10):
                if line:
                    line = line.decode("utf-8")
                    # Remove 'data: ' prefix if present
                    if line.startswith("data: "):
                        line = line[6:]
                    result += line
            return result

        # Handle JSON response
        elif response.get("contentType") == "application/json":
            content = []
            for chunk in response.get("response", []):
                content.append(chunk.decode('utf-8'))
            response_data = json.loads(''.join(content))
            return json.dumps(response_data)

        # Handle other response types
        else:
            response_body = response['response'].read()
            return response_body.decode('utf-8')

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return f"Error invoking specialist agent: {str(e)}\nDetails: {error_details}"

@tool
def call_specialist_agent(query: str) -> Dict[str, Any]:
    """
    Call the specialist agent for detailed analysis or complex tasks.
    Use this tool when you need expert analysis or detailed information.

    Args:
        query: The question or task to send to the specialist agent

    Returns:
        The specialist agent's response
    """
    result = invoke_specialist(query)
    return {
        "status": "success",
        "content": [{"text": result}]
    }

def create_orchestrator_agent() -> Agent:
    """Create the orchestrator agent with the tool to call specialist agent"""
    system_prompt = """You are an orchestrator agent.
    You can handle simple queries directly, but for complex analytical tasks,
    you should delegate to the specialist agent using the call_specialist_agent tool.

    Use the specialist agent when:
    - The query requires detailed analysis
    - The query is about complex topics
    - The user explicitly asks for expert analysis

    Handle simple queries (greetings, basic questions) yourself."""

    return Agent(
        tools=[call_specialist_agent],
        system_prompt=system_prompt,
        name="OrchestratorAgent"
    )

@app.entrypoint
async def invoke(payload=None):
    """Main entrypoint for orchestrator agent"""
    try:
        # Get the query from payload
        query = payload.get("prompt", "Hello, how are you?") if payload else "Hello, how are you?"

        # Create and use the orchestrator agent
        agent = create_orchestrator_agent()
        response = agent(query)

        return {
            "status": "success",
            "agent": "orchestrator",
            "response": response.message['content'][0]['text']
        }

    except Exception as e:
        return {
            "status": "error",
            "agent": "orchestrator",
            "error": str(e)
        }

if __name__ == "__main__":
    app.run()
```

### agent-orchestrator-code/requirements.txt

```
strands-agents
boto3>=1.40.0
botocore>=1.40.0
bedrock-agentcore
```

### agent-specialist-code/Dockerfile

```
FROM public.ecr.aws/docker/library/python:3.11-slim
WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
RUN pip install aws-opentelemetry-distro>=0.10.1

# Create non-root user
RUN useradd -m -u 1000 bedrock_agentcore
USER bedrock_agentcore

EXPOSE 8080
EXPOSE 8000

COPY . .

CMD ["opentelemetry-instrument", "python", "-m", "agent"]
```

### agent-specialist-code/agent.py

```
from strands import Agent
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

def create_specialist_agent() -> Agent:
    """Create a specialist agent that handles specific analytical tasks"""
    system_prompt = """You are a specialist analytical agent.
    You are an expert at analyzing data and providing detailed insights.
    When asked questions, provide thorough, well-reasoned responses with specific details.
    Focus on accuracy and completeness in your answers."""

    return Agent(
        system_prompt=system_prompt,
        name="SpecialistAgent"
    )

@app.entrypoint
async def invoke(payload=None):
    """Main entrypoint for specialist agent"""
    try:
        # Get the query from payload
        query = payload.get("prompt", "Hello") if payload else "Hello"

        # Create and use the specialist agent
        agent = create_specialist_agent()
        response = agent(query)

        return {
            "status": "success",
            "agent": "specialist",
            "response": response.message['content'][0]['text']
        }

    except Exception as e:
        return {
            "status": "error",
            "agent": "specialist",
            "error": str(e)
        }

if __name__ == "__main__":
    app.run()
```

### agent-specialist-code/requirements.txt

```
strands-agents
boto3>=1.40.0
botocore>=1.40.0
bedrock-agentcore
```
