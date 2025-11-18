### app.py:

```
#!/usr/bin/env python3
import aws_cdk as cdk
from basic_runtime_stack import BasicRuntimeStack

app = cdk.App()
BasicRuntimeStack(app, "BasicAgentDemo")

app.synth()
```

### basic_runtime_stack.py

```
from aws_cdk import (
    Stack,
    aws_ecr as ecr,
    aws_codebuild as codebuild,
    aws_iam as iam,
    aws_lambda as lambda_,
    aws_s3_assets as s3_assets,
    aws_bedrockagentcore as bedrockagentcore,
    CustomResource,
    CfnParameter,
    CfnOutput,
    Duration,
    RemovalPolicy
)
from constructs import Construct
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'infra_utils'))
from agentcore_role import AgentCoreRole

class BasicRuntimeStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Parameters
        agent_name = CfnParameter(self, "AgentName",
            type="String",
            default="BasicAgent",
            description="Name for the agent runtime"
        )

        image_tag = CfnParameter(self, "ImageTag",
            type="String",
            default="latest", 
            description="Tag for the Docker image"
        )

        network_mode = CfnParameter(self, "NetworkMode",
            type="String", 
            default="PUBLIC",
            description="Network mode for AgentCore resources",
            allowed_values=["PUBLIC", "PRIVATE"]
        )

        # ECR Repository
        ecr_repository = ecr.Repository(self, "ECRRepository",
            repository_name=f"{self.stack_name.lower()}-basic-agent",
            image_tag_mutability=ecr.TagMutability.MUTABLE,
            removal_policy=RemovalPolicy.DESTROY,
            empty_on_delete=True,
            image_scan_on_push=True
        )

        # S3 Asset for source code
        source_asset = s3_assets.Asset(self, "SourceAsset",
            path="./agent-code"
        )

        # CodeBuild Role
        codebuild_role = iam.Role(self, "CodeBuildRole",
            role_name=f"{self.stack_name}-codebuild-role",
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            inline_policies={
                "CodeBuildPolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="CloudWatchLogs",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:CreateLogGroup",
                                "logs:CreateLogStream", 
                                "logs:PutLogEvents"
                            ],
                            resources=[f"arn:aws:logs:{self.region}:{self.account}:log-group:/aws/codebuild/*"]
                        ),
                        iam.PolicyStatement(
                            sid="ECRAccess",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ecr:BatchCheckLayerAvailability",
                                "ecr:GetDownloadUrlForLayer",
                                "ecr:BatchGetImage",
                                "ecr:GetAuthorizationToken",
                                "ecr:PutImage",
                                "ecr:InitiateLayerUpload",
                                "ecr:UploadLayerPart",
                                "ecr:CompleteLayerUpload"
                            ],
                            resources=[ecr_repository.repository_arn, "*"]
                        ),
                        iam.PolicyStatement(
                            sid="S3SourceAccess",
                            effect=iam.Effect.ALLOW,
                            actions=["s3:GetObject"],
                            resources=[f"{source_asset.bucket.bucket_arn}/*"]
                        )
                    ]
                )
            }
        )

        # CodeBuild Project
        build_project = codebuild.Project(self, "AgentImageBuildProject",
            project_name=f"{self.stack_name}-basic-agent-build",
            description=f"Build basic agent Docker image for {self.stack_name}",
            role=codebuild_role,
            environment=codebuild.BuildEnvironment(
                build_image=codebuild.LinuxArmBuildImage.AMAZON_LINUX_2_STANDARD_3_0,
                compute_type=codebuild.ComputeType.LARGE,
                privileged=True
            ),
            source=codebuild.Source.s3(
                bucket=source_asset.bucket,
                path=source_asset.s3_object_key
            ),
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "pre_build": {
                        "commands": [
                            "echo Logging in to Amazon ECR...",
                            "aws ecr get-login-password --region $AWS_DEFAULT_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com"
                        ]
                    },
                    "build": {
                        "commands": [
                            "echo Build started on `date`",
                            "echo Building the Docker image for basic agent ARM64...",
                            "docker build -t $IMAGE_REPO_NAME:$IMAGE_TAG .",
                            "docker tag $IMAGE_REPO_NAME:$IMAGE_TAG $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG"
                        ]
                    },
                    "post_build": {
                        "commands": [
                            "echo Build completed on `date`",
                            "echo Pushing the Docker image...",
                            "docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$IMAGE_REPO_NAME:$IMAGE_TAG",
                            "echo ARM64 Docker image pushed successfully"
                        ]
                    }
                }
            }),
            environment_variables={
                "AWS_DEFAULT_REGION": codebuild.BuildEnvironmentVariable(value=self.region),
                "AWS_ACCOUNT_ID": codebuild.BuildEnvironmentVariable(value=self.account),
                "IMAGE_REPO_NAME": codebuild.BuildEnvironmentVariable(value=ecr_repository.repository_name),
                "IMAGE_TAG": codebuild.BuildEnvironmentVariable(value=image_tag.value_as_string),
                "STACK_NAME": codebuild.BuildEnvironmentVariable(value=self.stack_name)
            }
        )

        # Lambda function to trigger and wait for CodeBuild
        build_trigger_function = lambda_.Function(self, "BuildTriggerFunction",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="infra_utils.build_trigger_lambda.handler",
            timeout=Duration.minutes(15),
            code=lambda_.Code.from_asset(".", exclude=["*.pyc", "__pycache__", "cdk.out"]),
            initial_policy=[
                iam.PolicyStatement(
                    effect=iam.Effect.ALLOW,
                    actions=["codebuild:StartBuild", "codebuild:BatchGetBuilds"],
                    resources=[build_project.project_arn]
                )
            ]
        )

        # Custom Resource using the Lambda function
        trigger_build = CustomResource(self, "TriggerImageBuild",
            service_token=build_trigger_function.function_arn,
            properties={
                "ProjectName": build_project.project_name
            }
        )

        # Create AgentCore execution role
        agent_role = AgentCoreRole(self, "AgentCoreRole")

        # Create AgentCore Runtime
        agent_runtime = bedrockagentcore.CfnRuntime(self, "AgentRuntime",
            agent_runtime_name=f"{self.stack_name.replace('-', '_')}_{agent_name.value_as_string}",
            agent_runtime_artifact=bedrockagentcore.CfnRuntime.AgentRuntimeArtifactProperty(
                container_configuration=bedrockagentcore.CfnRuntime.ContainerConfigurationProperty(
                    container_uri=f"{ecr_repository.repository_uri}:{image_tag.value_as_string}"
                )
            ),
            network_configuration=bedrockagentcore.CfnRuntime.NetworkConfigurationProperty(
                network_mode=network_mode.value_as_string
            ),
            protocol_configuration="HTTP",
            role_arn=agent_role.role_arn,
            description=f"Basic agent runtime for {self.stack_name}",
            environment_variables={
                "AWS_DEFAULT_REGION": self.region
            }
        )

        agent_runtime.node.add_dependency(trigger_build)

        # Outputs
        CfnOutput(self, "AgentRuntimeId",
            description="ID of the created agent runtime",
            value=agent_runtime.attr_agent_runtime_id
        )

        CfnOutput(self, "AgentRuntimeArn", 
            description="ARN of the created agent runtime",
            value=agent_runtime.attr_agent_runtime_arn
        )

        CfnOutput(self, "AgentRoleArn",
            description="ARN of the agent execution role",
            value=agent_role.role_arn
        )
```

### cdk.json

```
{
  "app": "python3 app.py",
  "watch": {
    "include": [
      "**"
    ],
    "exclude": [
      "README.md",
      "cdk*.json",
      "requirements*.txt",
      "source.bat",
      "**/__pycache__",
      "**/*.pyc"
    ]
  },
  "context": {
    "@aws-cdk/aws-lambda:recognizeLayerVersion": true,
    "@aws-cdk/core:checkSecretUsage": true,
    "@aws-cdk/core:target-partitions": [
      "aws",
      "aws-cn"
    ],
    "@aws-cdk-containers/ecs-service-extensions:enableDefaultLogDriver": true,
    "@aws-cdk/aws-ec2:uniqueImdsv2TemplateName": true,
    "@aws-cdk/aws-ecs:arnFormatIncludesClusterName": true,
    "@aws-cdk/aws-iam:minimizePolicies": true,
    "@aws-cdk/core:validateSnapshotRemovalPolicy": true,
    "@aws-cdk/aws-codepipeline:crossAccountKeyAliasStackSafeResourceName": true,
    "@aws-cdk/aws-s3:createDefaultLoggingPolicy": true,
    "@aws-cdk/aws-sns-subscriptions:restrictSqsDescryption": true,
    "@aws-cdk/aws-apigateway:disableCloudWatchRole": true,
    "@aws-cdk/core:enablePartitionLiterals": true,
    "@aws-cdk/aws-events:eventsTargetQueueSameAccount": true,
    "@aws-cdk/aws-iam:standardizedServicePrincipals": true,
    "@aws-cdk/aws-ecs:disableExplicitDeploymentControllerForCircuitBreaker": true,
    "@aws-cdk/aws-iam:importedRoleStackSafeDefaultPolicyName": true,
    "@aws-cdk/aws-s3:serverAccessLogsUseBucketPolicy": true,
    "@aws-cdk/aws-route53-patters:useCertificate": true,
    "@aws-cdk/customresources:installLatestAwsSdkDefault": false,
    "@aws-cdk/aws-rds:databaseProxyUniqueResourceName": true,
    "@aws-cdk/aws-codedeploy:removeAlarmsFromDeploymentGroup": true,
    "@aws-cdk/aws-apigateway:authorizerChangeDeploymentLogicalId": true,
    "@aws-cdk/aws-ec2:launchTemplateDefaultUserData": true,
    "@aws-cdk/aws-secretsmanager:useAttachedSecretResourcePolicyForSecretTargetAttachments": true,
    "@aws-cdk/aws-redshift:columnId": true,
    "@aws-cdk/aws-stepfunctions-tasks:enableLogging": true,
    "@aws-cdk/aws-ec2:restrictDefaultSecurityGroup": true,
    "@aws-cdk/aws-apigateway:requestValidatorUniqueId": true,
    "@aws-cdk/aws-kms:aliasNameRef": true,
    "@aws-cdk/aws-autoscaling:generateLaunchTemplateInsteadOfLaunchConfig": true,
    "@aws-cdk/core:includePrefixInUniqueNameGeneration": true,
    "@aws-cdk/aws-efs:denyAnonymousAccess": true,
    "@aws-cdk/aws-opensearchservice:enableLogging": true,
    "@aws-cdk/aws-nordicapis-apigateway:authorizerChangeDeploymentLogicalId": true,
    "@aws-cdk/aws-ec2:ebsDefaultGp3Volume": true,
    "@aws-cdk/aws-ecs-patterns:removeDefaultDesiredCount": true,
    "@aws-cdk/aws-rds:preventRenderingDeprecatedCredentials": true,
    "@aws-cdk/aws-codepipeline-actions:useNewDefaultBranchForSourceAction": true
  }
}
```

### requirements.txt

```
aws-cdk-lib==2.218.0
constructs>=10.0.79
```

### agentcore/Dockerfile

```
FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir aws-opentelemetry-distro==0.10.1

ENV AWS_REGION=us-west-2
ENV AWS_DEFAULT_REGION=us-west-2

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

### agentcore/basic_agent.py

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

### infra_utils/agentcore_role.py

```
from aws_cdk import (
    aws_iam as iam,
    Stack
)
from constructs import Construct

class AgentCoreRole(iam.Role):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        region = Stack.of(scope).region
        account_id = Stack.of(scope).account

        super().__init__(scope, construct_id,
            assumed_by=iam.ServicePrincipal("bedrock-agentcore.amazonaws.com"),
            inline_policies={
                "AgentCorePolicy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            sid="ECRImageAccess",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "ecr:BatchGetImage",
                                "ecr:GetDownloadUrlForLayer",
                                "ecr:BatchCheckLayerAvailability"
                            ],
                            resources=[f"arn:aws:ecr:{region}:{account_id}:repository/*"]
                        ),
                        iam.PolicyStatement(
                            sid="ECRTokenAccess", 
                            effect=iam.Effect.ALLOW,
                            actions=["ecr:GetAuthorizationToken"],
                            resources=["*"]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "logs:DescribeLogStreams",
                                "logs:CreateLogGroup",
                                "logs:DescribeLogGroups",
                                "logs:CreateLogStream", 
                                "logs:PutLogEvents"
                            ],
                            resources=[f"arn:aws:logs:{region}:{account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "xray:PutTraceSegments",
                                "xray:PutTelemetryRecords", 
                                "xray:GetSamplingRules",
                                "xray:GetSamplingTargets"
                            ],
                            resources=["*"]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=["cloudwatch:PutMetricData"],
                            resources=["*"],
                            conditions={
                                "StringEquals": {
                                    "cloudwatch:namespace": "bedrock-agentcore"
                                }
                            }
                        ),
                        iam.PolicyStatement(
                            sid="GetAgentAccessToken",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "bedrock-agentcore:GetWorkloadAccessToken",
                                "bedrock-agentcore:GetWorkloadAccessTokenForJWT", 
                                "bedrock-agentcore:GetWorkloadAccessTokenForUserId"
                            ],
                            resources=[
                                f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default",
                                f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default/workload-identity/*"
                            ]
                        ),
                        iam.PolicyStatement(
                            sid="BedrockModelInvocation",
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "bedrock:InvokeModel",
                                "bedrock:InvokeModelWithResponseStream"
                            ],
                            resources=[
                                "arn:aws:bedrock:*::foundation-model/*",
                                f"arn:aws:bedrock:{region}:{account_id}:*"
                            ]
                        )
                    ]
                )
            },
            **kwargs
        )
```

### infra_utils/build_trigger_lambda.py

```
import boto3
import json
import logging
import time
import urllib3

# Note: cfnresponse is only available for inline Lambda code in CloudFormation.
# When using CDK with Code.from_asset(), we need to include our own copy.
# This is the standard AWS-provided cfnresponse module embedded directly.

class cfnresponse:
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

    @staticmethod
    def send(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False, reason=None):
        responseUrl = event['ResponseURL']
        print(responseUrl)

        responseBody = {
            'Status': responseStatus,
            'Reason': reason or "See the details in CloudWatch Log Stream: {}".format(context.log_stream_name),
            'PhysicalResourceId': physicalResourceId or context.log_stream_name,
            'StackId': event['StackId'],
            'RequestId': event['RequestId'],
            'LogicalResourceId': event['LogicalResourceId'],
            'NoEcho': noEcho,
            'Data': responseData
        }

        json_responseBody = json.dumps(responseBody)
        print("Response body:")
        print(json_responseBody)

        headers = {
            'content-type': '',
            'content-length': str(len(json_responseBody))
        }

        try:
            http = urllib3.PoolManager()
            response = http.request('PUT', responseUrl, headers=headers, body=json_responseBody)
            print("Status code:", response.status)
        except Exception as e:
            print("send(..) failed executing http.request(..):", e)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def handler(event, context):
    logger.info('Received event: %s', json.dumps(event))

    try:
        if event['RequestType'] == 'Delete':
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
            return

        project_name = event['ResourceProperties']['ProjectName']

        codebuild = boto3.client('codebuild')

        # Start build
        response = codebuild.start_build(projectName=project_name)
        build_id = response['build']['id']
        logger.info(f"Started build: {build_id}")

        # Wait for completion
        max_wait_time = context.get_remaining_time_in_millis() / 1000 - 30
        start_time = time.time()

        while True:
            if time.time() - start_time > max_wait_time:
                cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': 'Build timeout'})
                return

            build_response = codebuild.batch_get_builds(ids=[build_id])
            build_status = build_response['builds'][0]['buildStatus']

            if build_status == 'SUCCEEDED':
                logger.info(f"Build {build_id} succeeded")
                cfnresponse.send(event, context, cfnresponse.SUCCESS, {'BuildId': build_id})
                return
            elif build_status in ['FAILED', 'FAULT', 'STOPPED', 'TIMED_OUT']:
                logger.error(f"Build {build_id} failed with status: {build_status}")
                cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': f'Build failed: {build_status}'})
                return

            logger.info(f"Build {build_id} status: {build_status}")
            time.sleep(30)

    except Exception as e:
        logger.error('Error: %s', str(e))
        cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': str(e)})
```
