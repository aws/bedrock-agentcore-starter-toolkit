# AWS Bedrock Agent Infrastructure

This directory contains Infrastructure as Code (IaC) and deployment scripts for the AWS Bedrock Agent fraud detection system.

## Overview

The infrastructure includes:
- **AWS Bedrock Agent**: AI agent with Claude 3 Sonnet model
- **Action Groups**: Tool integrations for identity verification, fraud database, and geolocation
- **Knowledge Base**: Vector database for fraud patterns and rules
- **IAM Roles**: Proper permissions for agent, knowledge base, and Lambda functions
- **Lambda Functions**: Action group executors
- **CloudWatch**: Logging and monitoring

## Files

- `bedrock_agent_config.py`: Python SDK for configuring Bedrock Agent
- `iam_roles.py`: IAM role and policy management
- `cloudformation_template.yaml`: CloudFormation template for infrastructure
- `deploy_bedrock_agent.py`: Orchestration script for Bedrock Agent deployment
- `data_storage_config.py`: DynamoDB and S3 configuration for data storage
- `streaming_config.py`: Kinesis, EventBridge, and Lambda configuration for streaming
- `monitoring_config.py`: CloudWatch dashboards, alarms, and X-Ray configuration
- `deploy_full_infrastructure.py`: Complete infrastructure deployment orchestrator
- `README.md`: This file

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials
3. **Python 3.11+** installed
4. **Boto3** library installed:
   ```bash
   pip install boto3
   ```

## Deployment

### Quick Start - Full Infrastructure

Deploy complete infrastructure (recommended):

```bash
python deploy_full_infrastructure.py --environment dev --region us-east-1
```

This will deploy:
- IAM roles and permissions
- DynamoDB tables and S3 buckets
- Kinesis streams and Lambda functions
- AWS Bedrock Agent with action groups
- CloudWatch dashboards and alarms
- X-Ray tracing

### Quick Start - Bedrock Agent Only

Deploy only Bedrock Agent (requires existing IAM roles):

```bash
python deploy_bedrock_agent.py --environment dev --region us-east-1
```

### Step-by-Step Deployment

#### 1. Create IAM Roles

```bash
python iam_roles.py
```

This creates:
- `BedrockAgentFraudDetectionRole`: For agent execution
- `BedrockKnowledgeBaseFraudPatternsRole`: For knowledge base access
- `BedrockAgentActionGroupLambdaRole`: For Lambda function execution

#### 2. Deploy CloudFormation Stack

```bash
aws cloudformation create-stack \
  --stack-name fraud-detection-bedrock-agent-dev \
  --template-body file://cloudformation_template.yaml \
  --parameters ParameterKey=Environment,ParameterValue=dev \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

Wait for stack creation:

```bash
aws cloudformation wait stack-create-complete \
  --stack-name fraud-detection-bedrock-agent-dev \
  --region us-east-1
```

#### 3. Configure Bedrock Agent

```python
from bedrock_agent_config import setup_fraud_detection_agent

# Get role ARNs from CloudFormation outputs
agent_role_arn = "arn:aws:iam::ACCOUNT_ID:role/BedrockAgentFraudDetection-dev"
kb_role_arn = "arn:aws:iam::ACCOUNT_ID:role/BedrockKnowledgeBaseFraudPatterns-dev"

# Setup agent
agent_details = setup_fraud_detection_agent(
    region_name="us-east-1",
    agent_role_arn=agent_role_arn,
    knowledge_base_role_arn=kb_role_arn
)

print(f"Agent ID: {agent_details['agent_id']}")
```

### Component-Specific Deployment

**Data Storage Only:**
```bash
python data_storage_config.py --environment dev --region us-east-1
```

**Streaming Infrastructure Only:**
```bash
python streaming_config.py --environment dev --region us-east-1 --lambda-role-arn <ROLE_ARN>
```

**Monitoring Only:**
```bash
python monitoring_config.py --environment dev --region us-east-1
```

### Environment-Specific Deployment

**Development:**
```bash
python deploy_full_infrastructure.py --environment dev
```

**Staging:**
```bash
python deploy_full_infrastructure.py --environment staging
```

**Production:**
```bash
python deploy_full_infrastructure.py --environment prod
```

## Configuration

### Agent Configuration

The agent is configured with:
- **Model**: Claude 3 Sonnet (`anthropic.claude-3-sonnet-20240229-v1:0`)
- **Instruction**: Specialized fraud detection prompt
- **Session TTL**: 600 seconds (10 minutes)

### Action Groups

Three action groups are configured:

1. **Identity Verification**
   - Verifies user identity
   - Checks for account compromise
   - Lambda function: `bedrock-agent-identity-verification-{env}`

2. **Fraud Database**
   - Queries fraud database for similar cases
   - Cross-references known fraud patterns
   - Lambda function: `bedrock-agent-fraud-database-{env}`

3. **Geolocation**
   - Assesses location risk
   - Verifies travel patterns
   - Lambda function: `bedrock-agent-geolocation-{env}`

### Knowledge Base

- **Name**: `fraud-patterns-kb`
- **Embedding Model**: Amazon Titan Embed Text v1
- **Storage**: OpenSearch Serverless
- **S3 Bucket**: `fraud-detection-knowledge-base-{env}-{account-id}`

### Agent Aliases

Three aliases are created for each environment:
- `dev`: Development testing
- `staging`: Pre-production validation
- `prod`: Production deployment

## Usage

### Invoke Agent via Python SDK

```python
import boto3

bedrock_agent_runtime = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

response = bedrock_agent_runtime.invoke_agent(
    agentId='AGENT_ID',
    agentAliasId='ALIAS_ID',
    sessionId='session-123',
    inputText='Analyze transaction: user_123, amount $5000, location Russia'
)

# Process response
for event in response['completion']:
    if 'chunk' in event:
        chunk = event['chunk']
        print(chunk['bytes'].decode('utf-8'))
```

### Invoke Agent via AWS CLI

```bash
aws bedrock-agent-runtime invoke-agent \
  --agent-id AGENT_ID \
  --agent-alias-id ALIAS_ID \
  --session-id session-123 \
  --input-text "Analyze transaction for fraud" \
  --region us-east-1
```

## Monitoring

### CloudWatch Logs

Agent logs are stored in:
```
/aws/bedrock/agent/fraud-detection-{environment}
```

View logs:
```bash
aws logs tail /aws/bedrock/agent/fraud-detection-dev --follow
```

### CloudWatch Metrics

Monitor agent performance:
- Invocation count
- Error rate
- Latency
- Token usage

## Infrastructure Components

### Data Storage

**DynamoDB Tables:**
- `fraud-detection-transactions-{env}`: Transaction history with TTL
- `fraud-detection-decisions-{env}`: Decision context and memory
- `fraud-detection-user-profiles-{env}`: User behavior profiles
- `fraud-detection-patterns-{env}`: Learned fraud patterns

**S3 Buckets:**
- `fraud-detection-audit-logs-{env}-{account}`: Audit logs with lifecycle policies
- `fraud-detection-decision-trails-{env}-{account}`: Decision trails
- `fraud-detection-models-{env}-{account}`: ML model artifacts

### Streaming Infrastructure

**Kinesis Streams:**
- `fraud-detection-transactions-{env}`: Transaction ingestion (ON_DEMAND)
- `fraud-detection-events-{env}`: Fraud events (ON_DEMAND)

**Lambda Functions:**
- `fraud-detection-stream-processor-{env}`: Process transaction streams
- `fraud-detection-alert-handler-{env}`: Handle fraud alerts

**EventBridge Rules:**
- `fraud-detection-events-{env}`: Route fraud detection events

**Dead Letter Queues:**
- `fraud-detection-dlq-{env}`: Failed message handling

### Monitoring & Observability

**CloudWatch Dashboards:**
- `fraud-detection-{env}`: Comprehensive system metrics

**CloudWatch Alarms:**
- Lambda errors, duration, and throttles
- Kinesis iterator age and write throttles
- DynamoDB read/write throttles

**X-Ray Tracing:**
- Enabled on all Lambda functions for distributed tracing

**Custom Metrics:**
- `FraudDetection/TransactionsProcessed`
- `FraudDetection/FraudDetected`
- `FraudDetection/DetectionAccuracy`
- `FraudDetection/ProcessingLatency`

## Cleanup

### Delete All Infrastructure

```bash
# Delete in reverse order
python -c "
import boto3

# Delete Bedrock Agent
bedrock = boto3.client('bedrock-agent')
# bedrock.delete_agent(agentId='AGENT_ID')

# Delete Lambda functions
lambda_client = boto3.client('lambda')
# lambda_client.delete_function(FunctionName='function-name')

# Delete Kinesis streams
kinesis = boto3.client('kinesis')
# kinesis.delete_stream(StreamName='stream-name')

# Delete DynamoDB tables
dynamodb = boto3.client('dynamodb')
# dynamodb.delete_table(TableName='table-name')

# Delete S3 buckets (must be empty first)
s3 = boto3.client('s3')
# s3.delete_bucket(Bucket='bucket-name')
"
```

### Delete CloudFormation Stack

```bash
aws cloudformation delete-stack \
  --stack-name fraud-detection-bedrock-agent-dev \
  --region us-east-1
```

## Troubleshooting

### Common Issues

**Issue**: "Access Denied" when creating agent
- **Solution**: Ensure IAM roles have proper trust policies and permissions

**Issue**: Agent preparation fails
- **Solution**: Check that all action groups have valid Lambda ARNs

**Issue**: Knowledge base association fails
- **Solution**: Verify OpenSearch Serverless collection is created and accessible

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security Best Practices

1. **Least Privilege**: IAM roles have minimal required permissions
2. **Encryption**: All data encrypted at rest and in transit
3. **VPC**: Deploy Lambda functions in VPC for network isolation
4. **Secrets**: Store API keys in AWS Secrets Manager
5. **Audit**: Enable CloudTrail for all API calls

## Cost Optimization

- Use agent aliases to manage versions efficiently
- Set appropriate session TTL to avoid unnecessary charges
- Monitor token usage and optimize prompts
- Use S3 lifecycle policies for knowledge base data

## Support

For issues or questions:
1. Check CloudWatch logs for error details
2. Review IAM role permissions
3. Verify Bedrock service quotas
4. Contact AWS Support if needed

## References

- [AWS Bedrock Agent Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [Claude 3 Model Documentation](https://docs.anthropic.com/claude/docs)
- [AWS CloudFormation Documentation](https://docs.aws.amazon.com/cloudformation/)
