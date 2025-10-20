# AWS Infrastructure Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the complete AWS infrastructure for the fraud detection system with AI agent capabilities.

## Architecture Overview

The infrastructure consists of five main components:

1. **IAM Roles & Permissions** - Security and access control
2. **Data Storage** - DynamoDB tables and S3 buckets
3. **Streaming Infrastructure** - Kinesis streams, Lambda functions, EventBridge
4. **AWS Bedrock Agent** - AI agent with Claude model and action groups
5. **Monitoring & Observability** - CloudWatch dashboards, alarms, X-Ray tracing

## Prerequisites

### Required Tools

- **AWS CLI** (v2.x or higher)
- **Python** (3.11 or higher)
- **Boto3** library
- **AWS Account** with appropriate permissions

### AWS Permissions Required

Your AWS user/role needs permissions for:
- IAM (create roles and policies)
- DynamoDB (create tables)
- S3 (create buckets)
- Kinesis (create streams)
- Lambda (create functions)
- EventBridge (create rules)
- CloudWatch (create dashboards and alarms)
- SNS (create topics)
- SQS (create queues)
- Bedrock (create agents and knowledge bases)
- X-Ray (enable tracing)

### Installation

```bash
# Install Python dependencies
pip install boto3

# Configure AWS credentials
aws configure
```

## Deployment Options

### Option 1: Full Infrastructure Deployment (Recommended)

Deploy all components in one command:

```bash
cd aws_infrastructure
python deploy_full_infrastructure.py --environment dev --region us-east-1
```

**What this deploys:**
- ✓ IAM roles for Bedrock Agent, Lambda, and Knowledge Base
- ✓ 4 DynamoDB tables (transactions, decisions, user profiles, patterns)
- ✓ 3 S3 buckets (audit logs, decision trails, model artifacts)
- ✓ 2 Kinesis streams (transactions, events)
- ✓ 2 Lambda functions (stream processor, alert handler)
- ✓ EventBridge rules for event routing
- ✓ Dead letter queue for failed processing
- ✓ AWS Bedrock Agent with Claude 3 Sonnet
- ✓ 3 action groups (identity verification, fraud database, geolocation)
- ✓ Knowledge base for fraud patterns
- ✓ CloudWatch dashboard with 6 widgets
- ✓ 15+ CloudWatch alarms
- ✓ SNS topic for alarm notifications
- ✓ X-Ray tracing enabled

**Deployment time:** ~10-15 minutes

### Option 2: Component-by-Component Deployment

Deploy individual components for testing or troubleshooting:

#### Step 1: IAM Roles

```bash
python iam_roles.py
```

#### Step 2: Data Storage

```bash
python data_storage_config.py --environment dev --region us-east-1
```

#### Step 3: Streaming Infrastructure

```bash
# Get Lambda role ARN from Step 1
python streaming_config.py \
  --environment dev \
  --region us-east-1 \
  --lambda-role-arn arn:aws:iam::ACCOUNT_ID:role/BedrockAgentActionGroupLambdaRole
```

#### Step 4: Bedrock Agent

```bash
python deploy_bedrock_agent.py --environment dev --region us-east-1
```

#### Step 5: Monitoring

```bash
python monitoring_config.py --environment dev --region us-east-1
```

### Option 3: CloudFormation Template

Use the CloudFormation template for infrastructure as code:

```bash
aws cloudformation create-stack \
  --stack-name fraud-detection-bedrock-agent-dev \
  --template-body file://cloudformation_template.yaml \
  --parameters ParameterKey=Environment,ParameterValue=dev \
  --capabilities CAPABILITY_NAMED_IAM \
  --region us-east-1
```

## Post-Deployment Configuration

### 1. Subscribe to Alarm Notifications

```bash
# Get SNS topic ARN from deployment output
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:fraud-detection-alarms-dev \
  --protocol email \
  --notification-endpoint your-email@example.com

# Confirm subscription via email
```

### 2. Upload Fraud Patterns to Knowledge Base

```bash
# Create sample fraud patterns
cat > fraud_patterns.txt << EOF
Common fraud indicators:
- Multiple transactions from different locations within short time
- Unusual transaction amounts significantly higher than user average
- Transactions from high-risk countries
- Rapid succession of small test transactions followed by large transaction
EOF

# Upload to S3 knowledge base bucket
aws s3 cp fraud_patterns.txt \
  s3://fraud-detection-knowledge-base-dev-ACCOUNT_ID/fraud-patterns/

# Sync knowledge base
aws bedrock-agent start-ingestion-job \
  --knowledge-base-id KB_ID \
  --data-source-id DS_ID
```

### 3. Test the System

```bash
# Send test transaction to Kinesis stream
aws kinesis put-record \
  --stream-name fraud-detection-transactions-dev \
  --partition-key user123 \
  --data '{"transaction_id":"tx123","user_id":"user123","amount":5000,"currency":"USD"}'

# Check CloudWatch Logs
aws logs tail /aws/lambda/fraud-detection-stream-processor-dev --follow
```

### 4. View Dashboard

Navigate to CloudWatch Console:
```
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=fraud-detection-dev
```

## Environment-Specific Deployments

### Development Environment

```bash
python deploy_full_infrastructure.py --environment dev --region us-east-1
```

**Characteristics:**
- Lower retention periods
- Smaller capacity settings
- Cost-optimized configuration

### Staging Environment

```bash
python deploy_full_infrastructure.py --environment staging --region us-east-1
```

**Characteristics:**
- Production-like configuration
- Extended retention periods
- Performance testing ready

### Production Environment

```bash
python deploy_full_infrastructure.py --environment prod --region us-east-1
```

**Characteristics:**
- High availability configuration
- Maximum retention periods
- Enhanced monitoring and alerting
- Multi-region support (manual configuration)

## Monitoring and Maintenance

### View System Health

```bash
# Check Lambda function metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=fraud-detection-stream-processor-dev \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 3600 \
  --statistics Sum

# Check Kinesis stream metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kinesis \
  --metric-name IncomingRecords \
  --dimensions Name=StreamName,Value=fraud-detection-transactions-dev \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z \
  --period 3600 \
  --statistics Sum
```

### View Logs

```bash
# Lambda function logs
aws logs tail /aws/lambda/fraud-detection-stream-processor-dev --follow

# Bedrock Agent logs
aws logs tail /aws/bedrock/agent/fraud-detection-dev --follow
```

### View X-Ray Traces

```bash
# Get trace summaries
aws xray get-trace-summaries \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-01T23:59:59Z

# Get specific trace
aws xray batch-get-traces --trace-ids TRACE_ID
```

## Troubleshooting

### Common Issues

#### Issue: IAM Role Propagation Delay

**Symptom:** "Access Denied" errors immediately after deployment

**Solution:** Wait 10-30 seconds for IAM roles to propagate globally

```bash
sleep 30
```

#### Issue: Lambda Function Timeout

**Symptom:** Lambda functions timing out during processing

**Solution:** Increase timeout in configuration

```python
# In streaming_config.py, modify:
timeout=120  # Increase from 60 to 120 seconds
```

#### Issue: Kinesis Iterator Age High

**Symptom:** CloudWatch alarm for high iterator age

**Solution:** Increase Lambda concurrency or shard count

```bash
# Increase shard count
aws kinesis update-shard-count \
  --stream-name fraud-detection-transactions-dev \
  --target-shard-count 4 \
  --scaling-type UNIFORM_SCALING
```

#### Issue: DynamoDB Throttling

**Symptom:** ReadThrottleEvents or WriteThrottleEvents alarms

**Solution:** Switch to on-demand billing or increase provisioned capacity

```bash
# Switch to on-demand
aws dynamodb update-table \
  --table-name fraud-detection-transactions-dev \
  --billing-mode PAY_PER_REQUEST
```

#### Issue: Bedrock Agent Preparation Failed

**Symptom:** Agent status shows "FAILED"

**Solution:** Check action group Lambda ARNs and permissions

```bash
# Verify Lambda function exists
aws lambda get-function --function-name bedrock-agent-identity-verification-dev

# Add Bedrock invoke permission
aws lambda add-permission \
  --function-name bedrock-agent-identity-verification-dev \
  --statement-id AllowBedrockInvoke \
  --action lambda:InvokeFunction \
  --principal bedrock.amazonaws.com
```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Resource Status

```bash
# DynamoDB tables
aws dynamodb list-tables | grep fraud-detection

# S3 buckets
aws s3 ls | grep fraud-detection

# Kinesis streams
aws kinesis list-streams | grep fraud-detection

# Lambda functions
aws lambda list-functions | grep fraud-detection

# Bedrock agents
aws bedrock-agent list-agents
```

## Cost Optimization

### Estimated Monthly Costs (Development)

- **DynamoDB:** $5-20 (on-demand)
- **S3:** $1-5 (with lifecycle policies)
- **Kinesis:** $15-30 (on-demand)
- **Lambda:** $5-15 (based on invocations)
- **Bedrock Agent:** $50-200 (based on usage)
- **CloudWatch:** $5-10 (logs and metrics)

**Total:** ~$80-280/month for development environment

### Cost Reduction Tips

1. **Use lifecycle policies** to transition old data to cheaper storage
2. **Enable DynamoDB TTL** to automatically delete old records
3. **Use on-demand billing** for variable workloads
4. **Set CloudWatch log retention** to 7-30 days
5. **Use reserved capacity** for production workloads

## Security Best Practices

### 1. Encryption

- ✓ All DynamoDB tables use KMS encryption
- ✓ All S3 buckets use server-side encryption
- ✓ Kinesis streams use KMS encryption
- ✓ SQS queues use KMS encryption

### 2. Access Control

- ✓ IAM roles follow least privilege principle
- ✓ S3 buckets block public access
- ✓ Lambda functions run in VPC (optional)

### 3. Audit and Compliance

- ✓ CloudTrail enabled for all API calls
- ✓ CloudWatch Logs for all components
- ✓ X-Ray tracing for distributed visibility
- ✓ Immutable audit logs in S3

### 4. Network Security

```bash
# Optional: Deploy Lambda in VPC
aws lambda update-function-configuration \
  --function-name fraud-detection-stream-processor-dev \
  --vpc-config SubnetIds=subnet-xxx,SecurityGroupIds=sg-xxx
```

## Cleanup

### Delete All Resources

```bash
# WARNING: This will delete all data!

# 1. Delete Bedrock Agent
aws bedrock-agent delete-agent --agent-id AGENT_ID

# 2. Delete Lambda functions
aws lambda delete-function --function-name fraud-detection-stream-processor-dev
aws lambda delete-function --function-name fraud-detection-alert-handler-dev

# 3. Delete EventBridge rules
aws events remove-targets --rule fraud-detection-events-dev --ids 1
aws events delete-rule --name fraud-detection-events-dev

# 4. Delete Kinesis streams
aws kinesis delete-stream --stream-name fraud-detection-transactions-dev
aws kinesis delete-stream --stream-name fraud-detection-events-dev

# 5. Empty and delete S3 buckets
aws s3 rm s3://fraud-detection-audit-logs-dev-ACCOUNT_ID --recursive
aws s3 rb s3://fraud-detection-audit-logs-dev-ACCOUNT_ID

# 6. Delete DynamoDB tables
aws dynamodb delete-table --table-name fraud-detection-transactions-dev
aws dynamodb delete-table --table-name fraud-detection-decisions-dev
aws dynamodb delete-table --table-name fraud-detection-user-profiles-dev
aws dynamodb delete-table --table-name fraud-detection-patterns-dev

# 7. Delete CloudWatch resources
aws cloudwatch delete-dashboards --dashboard-names fraud-detection-dev
aws cloudwatch delete-alarms --alarm-names $(aws cloudwatch describe-alarms --query 'MetricAlarms[?contains(AlarmName, `fraud-detection-dev`)].AlarmName' --output text)

# 8. Delete SNS topics
aws sns delete-topic --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:fraud-detection-alarms-dev

# 9. Delete SQS queues
aws sqs delete-queue --queue-url https://sqs.us-east-1.amazonaws.com/ACCOUNT_ID/fraud-detection-dlq-dev

# 10. Delete IAM roles (last)
aws iam delete-role --role-name BedrockAgentFraudDetectionRole
aws iam delete-role --role-name BedrockKnowledgeBaseFraudPatternsRole
aws iam delete-role --role-name BedrockAgentActionGroupLambdaRole
```

## Support and Resources

### Documentation

- [AWS Bedrock Agent Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents.html)
- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [Amazon Kinesis Documentation](https://docs.aws.amazon.com/kinesis/)
- [Amazon DynamoDB Documentation](https://docs.aws.amazon.com/dynamodb/)

### Getting Help

1. Check CloudWatch Logs for error details
2. Review IAM role permissions
3. Verify service quotas and limits
4. Contact AWS Support if needed

### Service Quotas

Check and request quota increases:

```bash
# View current quotas
aws service-quotas list-service-quotas --service-code lambda
aws service-quotas list-service-quotas --service-code kinesis
aws service-quotas list-service-quotas --service-code dynamodb

# Request quota increase
aws service-quotas request-service-quota-increase \
  --service-code lambda \
  --quota-code L-B99A9384 \
  --desired-value 1000
```

## Next Steps

After successful deployment:

1. ✓ Subscribe to SNS alarm notifications
2. ✓ Upload fraud patterns to knowledge base
3. ✓ Test the system with sample transactions
4. ✓ Review CloudWatch dashboard
5. ✓ Configure additional alerting rules
6. ✓ Set up automated backups
7. ✓ Plan for production deployment
8. ✓ Document custom configurations
9. ✓ Train team on monitoring and operations
10. ✓ Establish incident response procedures
