# Runtime Permissions

This guide covers the IAM permissions required to run agents with Amazon Bedrock AgentCore Runtime. The toolkit supports two types of execution roles with distinct permission sets.

Refer to [AWS Bedrock AgentCore Runtime Permissions](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html) documentation for more details.

## Overview

The toolkit requires two types of IAM roles for different phases of agent deployment:

- **Runtime Execution Role**: Used by Bedrock AgentCore Runtime to execute your agent
- **CodeBuild Execution Role**: Used by AWS CodeBuild to build and push container images (ARM64 architecture)

Both roles can be automatically created by the toolkit or manually specified using existing roles.

## Auto Role Creation Feature

### Overview

The Bedrock AgentCore Starter Toolkit includes an **auto role creation feature** that automatically generates the Runtime Execution Role when you don't specify an existing role.

### What Gets Auto-Created

When you run `agentcore configure` without specifying the `--execution-role` parameter, the toolkit automatically creates:

#### Runtime Execution Role
- **Name**: `AmazonBedrockAgentCoreSDKRuntime-{region}-{hash}`
- **Purpose**: Used by Bedrock AgentCore to execute your agent
- **Permissions**: All required runtime permissions (ECR, CloudWatch, Bedrock, etc.)

> **Note**: The CodeBuild Execution Role (`AmazonBedrockAgentCoreSDKCodeBuild-{region}-{hash}`) is always auto-created when using CodeBuild deployment, regardless of this setting.

### Benefits of Auto Role Creation

**🚀 Instant Setup**
```bash
# One command creates everything you need
agentcore configure -e my_agent.py
```

### Usage Examples

**Basic Auto-Creation:**
```bash
# Creates all required roles and resources
agentcore configure -e my_agent.py
```

**Auto-Creation with Default Deployment:**
```bash
# Uses CodeBuild by default
agentcore configure -e my_agent.py
agentcore launch
```

## Developer/Caller Permissions

### Overview

Developers using the Bedrock AgentCore Starter Toolkit need specific IAM permissions to create roles, manage CodeBuild projects, and deploy agents. These permissions are separate from the execution roles and are required for the toolkit's operational functionality.

### Required Caller Policy

Attach the following policy to your IAM user or role:

```json
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Sid": "IAMRoleManagement",
			"Effect": "Allow",
			"Action": [
				"iam:CreateRole",
				"iam:DeleteRole",
				"iam:GetRole",
				"iam:PutRolePolicy",
				"iam:DeleteRolePolicy",
				"iam:AttachRolePolicy",
				"iam:DetachRolePolicy",
				"iam:TagRole",
				"iam:ListRolePolicies",
				"iam:ListAttachedRolePolicies"
			],
			"Resource": [
				"arn:aws:iam::*:role/*BedrockAgentCore*",
				"arn:aws:iam::*:role/service-role/*BedrockAgentCore*"
			]
		},
		{
			"Sid": "CodeBuildProjectAccess",
			"Effect": "Allow",
			"Action": [
				"codebuild:StartBuild",
				"codebuild:BatchGetBuilds",
				"codebuild:ListBuildsForProject",
				"codebuild:CreateProject",
				"codebuild:UpdateProject",
				"codebuild:BatchGetProjects"
			],
			"Resource": [
				"arn:aws:codebuild:*:*:project/bedrock-agentcore-*",
				"arn:aws:codebuild:*:*:build/bedrock-agentcore-*"
			]
		},
		{
			"Sid": "CodeBuildListAccess",
			"Effect": "Allow",
			"Action": [
				"codebuild:ListProjects"
			],
			"Resource": "*"
		},
		{
			"Sid": "IAMPassRoleAccess",
			"Effect": "Allow",
			"Action": [
				"iam:PassRole"
			],
			"Resource": [
				"arn:aws:iam::*:role/AmazonBedrockAgentCore*",
				"arn:aws:iam::*:role/service-role/AmazonBedrockAgentCore*"
			]
		},
		{
			"Sid": "CloudWatchLogsAccess",
			"Effect": "Allow",
			"Action": [
				"logs:GetLogEvents",
				"logs:DescribeLogGroups",
				"logs:DescribeLogStreams"
			],
			"Resource": [
				"arn:aws:logs:*:*:log-group:/aws/bedrock-agentcore/*",
				"arn:aws:logs:*:*:log-group:/aws/codebuild/*"
			]
		},
		{
			"Sid": "S3Access",
			"Effect": "Allow",
			"Action": [
				"s3:GetObject",
				"s3:PutObject",
				"s3:ListBucket",
				"s3:CreateBucket",
				"s3:PutLifecycleConfiguration"
			],
			"Resource": [
				"arn:aws:s3:::bedrock-agentcore-*",
				"arn:aws:s3:::bedrock-agentcore-*/*"
			]
		},
		{
			"Sid": "ECRRepositoryAccess",
			"Effect": "Allow",
			"Action": [
				"ecr:CreateRepository",
				"ecr:DescribeRepositories",
				"ecr:GetRepositoryPolicy",
				"ecr:InitiateLayerUpload",
				"ecr:CompleteLayerUpload",
				"ecr:PutImage",
				"ecr:UploadLayerPart",
				"ecr:BatchCheckLayerAvailability",
				"ecr:GetDownloadUrlForLayer",
				"ecr:BatchGetImage",
				"ecr:ListImages",
				"ecr:TagResource"
			],
			"Resource": [
				"arn:aws:ecr:*:*:repository/bedrock-agentcore-*"
			]
		},
		{
			"Sid": "ECRAuthorizationAccess",
			"Effect": "Allow",
			"Action": [
				"ecr:GetAuthorizationToken"
			],
			"Resource": "*"
		}
	]
}
```

### Additional Required Permissions

You also need:
- **AgentCore Full Access**: `BedrockAgentCoreFullAccess` managed policy
- **Bedrock Access** (one of the following):
  - **Option 1 (Development)**: `AmazonBedrockFullAccess` managed policy
  - **Option 2 (Production Recommended)**: Custom policy with scoped permissions for specific models and actions

## Production Security Best Practices

When moving from development to production, consider these security enhancements:

### 1. Scope Down Resource Access

Instead of granting broad access to all resources, limit permissions to specific resources:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LimitedModelAccess",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:region:accountId:foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
                "arn:aws:bedrock:region:accountId:foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
            ]
        },
        {
            "Sid": "LimitedECRAccess",
            "Effect": "Allow",
            "Action": [
                "ecr:BatchGetImage",
                "ecr:GetDownloadUrlForLayer"
            ],
            "Resource": [
                "arn:aws:ecr:region:accountId:repository/bedrock-agentcore-your-agent-name"
            ]
        }
    ]
}
```

### 2. Use Infrastructure as Code

Consider using AWS CDK, CloudFormation, or Terraform to define your roles with precise permissions.

### CodeBuild Integration

The toolkit uses AWS CodeBuild for ARM64 container builds, especially useful in cloud development environments where Docker is not available (such as SageMaker notebooks, Cloud9, or other managed environments).

## Runtime Execution Role

The Runtime Execution Role is an IAM role that AgentCore Runtime assumes to run an agent. Replace the following:

- `region` with the AWS Region that you are using
- `accountId` with your AWS account ID
- `agentName` with the name of your agent. You'll need to decide the agent name before creating the role and AgentCore Runtime.

### Permissions Policy

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ECRImageAccess",
            "Effect": "Allow",
            "Action": [
                "ecr:BatchGetImage",
                "ecr:GetDownloadUrlForLayer"
            ],
            "Resource": [
                "arn:aws:ecr:region:accountId:repository/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:DescribeLogStreams",
                "logs:CreateLogGroup"
            ],
            "Resource": [
                "arn:aws:logs:region:accountId:log-group:/aws/bedrock-agentcore/runtimes/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:DescribeLogGroups"
            ],
            "Resource": [
                "arn:aws:logs:region:accountId:log-group:*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": [
                "arn:aws:logs:region:accountId:log-group:/aws/bedrock-agentcore/runtimes/*:log-stream:*"
            ]
        },
        {
            "Sid": "ECRTokenAccess",
            "Effect": "Allow",
            "Action": [
                "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "xray:PutTraceSegments",
                "xray:PutTelemetryRecords",
                "xray:GetSamplingRules",
                "xray:GetSamplingTargets"
            ],
            "Resource": ["*"]
        },
        {
            "Effect": "Allow",
            "Resource": "*",
            "Action": "cloudwatch:PutMetricData",
            "Condition": {
                "StringEquals": {
                    "cloudwatch:namespace": "bedrock-agentcore"
                }
            }
        },
        {
            "Sid": "GetAgentAccessToken",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:GetWorkloadAccessToken",
                "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                "bedrock-agentcore:GetWorkloadAccessTokenForUserId"
            ],
            "Resource": [
                "arn:aws:bedrock-agentcore:region:accountId:workload-identity-directory/default",
                "arn:aws:bedrock-agentcore:region:accountId:workload-identity-directory/default/workload-identity/agentName-*"
            ]
        },
        {
            "Sid": "BedrockModelInvocation",
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream"
            ],
            "Resource": [
                "arn:aws:bedrock:*::foundation-model/*",
                "arn:aws:bedrock:region:accountId:*"
            ]
        }
    ]
}
```

### Trust Policy

The trust relationship for the AgentCore Runtime execution role should allow AgentCore Runtime to assume the role:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AssumeRolePolicy",
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock-agentcore.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
            "StringEquals": {
                "aws:SourceAccount": "accountId"
            },
            "ArnLike": {
                "aws:SourceArn": "arn:aws:bedrock-agentcore:region:accountId:*"
            }
       }
    }
  ]
}
```

## CodeBuild Execution Role

The CodeBuild Execution Role is used by AWS CodeBuild to build your agent's Docker container for ARM64 architecture and push it to Amazon ECR.

### Trust Policy

The CodeBuild execution role must trust the `codebuild.amazonaws.com` service:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "codebuild.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "YOUR_ACCOUNT_ID"
        }
      }
    }
  ]
}
```

### Permissions Policy

The CodeBuild execution role requires the following permissions:

#### ECR Repository Access
```json
{
  "Effect": "Allow",
  "Action": [
    "ecr:GetAuthorizationToken"
  ],
  "Resource": "*"
},
{
  "Effect": "Allow",
  "Action": [
    "ecr:BatchCheckLayerAvailability",
    "ecr:BatchGetImage",
    "ecr:GetDownloadUrlForLayer",
    "ecr:PutImage",
    "ecr:InitiateLayerUpload",
    "ecr:UploadLayerPart",
    "ecr:CompleteLayerUpload"
  ],
  "Resource": "arn:aws:ecr:YOUR_REGION:YOUR_ACCOUNT_ID:repository/YOUR_ECR_REPOSITORY"
}
```

**Purpose**: Allows CodeBuild to authenticate with ECR and push the built container image.

#### CloudWatch Logs for Build Process
```json
{
  "Effect": "Allow",
  "Action": [
    "logs:CreateLogGroup",
    "logs:CreateLogStream",
    "logs:PutLogEvents"
  ],
  "Resource": [
    "arn:aws:logs:YOUR_REGION:YOUR_ACCOUNT_ID:log-group:/aws/codebuild/bedrock-agentcore-*"
  ]
}
```

**Purpose**: Enables CodeBuild to create and write to log groups for build monitoring.

#### S3 Source Access
```json
{
  "Effect": "Allow",
  "Action": [
    "s3:GetObject"
  ],
  "Resource": [
    "arn:aws:s3:::bedrock-agentcore-codebuild-sources-YOUR_ACCOUNT_ID-YOUR_REGION/*"
  ]
}
```

**Purpose**: Allows CodeBuild to access the source code uploaded to the toolkit's managed S3 bucket.

## Toolkit Implementation Details

### Role Naming Convention

The toolkit uses deterministic naming for auto-created roles:

- **Runtime Role**: `AmazonBedrockAgentCoreSDKRuntime-{region}-{hash}`
- **CodeBuild Role**: `AmazonBedrockAgentCoreSDKCodeBuild-{region}-{hash}`

Where `{hash}` is a deterministic 10-character hash based on your agent name, ensuring consistent role names across deployments.
