# Troubleshooting Guide

## Overview

This guide provides solutions to common issues encountered with the Fraud Detection System.

## Quick Diagnostic Commands

```bash
# System health
curl https://api.fraud-detection.example.com/v1/health

# Recent errors
aws logs tail /aws/lambda/fraud-detection-stream-processor-prod --since 1h | grep ERROR

# Current metrics
python scripts/check_system_metrics.py

# Agent status
aws bedrock-agent list-agents --region us-east-1
```

## Common Issues

### 1. API Returns 500 Internal Server Error

**Symptoms**:
- API requests fail with 500 error
- Error message: "An unexpected error occurred"

**Possible Causes**:
- Lambda function error
- Database connection issue
- Bedrock agent unavailable
- Configuration error

**Diagnosis**:
```bash
# Check Lambda logs
aws logs tail /aws/lambda/fraud-detection-api-prod --since 15m

# Check database connectivity
aws dynamodb describe-table --table-name fraud-detection-transactions-prod

# Check Bedrock agent status
aws bedrock-agent get-agent --agent-id $AGENT_ID
```

**Solutions**:

1. **If Lambda error**:
   ```bash
   # Check function configuration
   aws lambda get-function-configuration --function-name fraud-detection-api-prod
   
   # Increase timeout if needed
   aws lambda update-function-configuration \
     --function-name fraud-detection-api-prod \
     --timeout 60
   ```

2. **If database issue**:
   ```bash
   # Check for throttling
   aws cloudwatch get-metric-statistics \
     --namespace AWS/DynamoDB \
     --metric-name UserErrors \
     --dimensions Name=TableName,Value=fraud-detection-transactions-prod \
     --start-time $(date -u -d "30 minutes ago" +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Sum
   
   # Switch to on-demand if throttled
   aws dynamodb update-table \
     --table-name fraud-detection-transactions-prod \
     --billing-mode PAY_PER_REQUEST
   ```

3. **If Bedrock agent issue**:
   ```bash
   # Prepare agent again
   aws bedrock-agent prepare-agent --agent-id $AGENT_ID
   
   # Check IAM permissions
   aws iam simulate-principal-policy \
     --policy-source-arn arn:aws:iam::ACCOUNT_ID:role/BedrockAgentFraudDetectionRole \
     --action-names bedrock:InvokeModel
   ```

### 2. High Response Times

**Symptoms**:
- API responses taking > 2 seconds
- Timeout errors
- Poor user experience

**Possible Causes**:
- High system load
- Database slow queries
- External API latency
- Insufficient resources

**Diagnosis**:
```bash
# Check X-Ray traces
aws xray get-trace-summaries \
  --start-time $(date -u -d "1 hour ago" +%s) \
  --end-time $(date -u +%s) \
  --filter-expression 'duration > 2'

# Check Lambda duration
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=fraud-detection-api-prod \
  --start-time $(date -u -d "1 hour ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum

# Check DynamoDB latency
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name SuccessfulRequestLatency \
  --dimensions Name=TableName,Value=fraud-detection-transactions-prod \
  --start-time $(date -u -d "1 hour ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

**Solutions**:

1. **Increase Lambda resources**:
   ```bash
   # Increase memory (also increases CPU)
   aws lambda update-function-configuration \
     --function-name fraud-detection-api-prod \
     --memory-size 2048
   
   # Increase concurrency
   aws lambda put-function-concurrency \
     --function-name fraud-detection-api-prod \
     --reserved-concurrent-executions 500
   ```

2. **Optimize database queries**:
   ```bash
   # Enable DAX for caching
   ./scripts/enable_dax.sh production
   
   # Add indexes if needed
   python scripts/optimize_dynamodb_indexes.py
   ```

3. **Enable caching**:
   ```bash
   # Increase cache TTL
   aws ssm put-parameter \
     --name /fraud-detection/cache/ttl \
     --value "600" \
     --overwrite
   
   # Enable Redis cache
   ./scripts/enable_redis_cache.sh production
   ```

### 3. Transactions Not Being Processed

**Symptoms**:
- Transactions stuck in queue
- Kinesis stream backlog growing
- No fraud detection results

**Possible Causes**:
- Lambda function errors
- Kinesis stream issues
- Event source mapping disabled
- Insufficient Lambda concurrency

**Diagnosis**:
```bash
# Check Kinesis iterator age
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kinesis \
  --metric-name GetRecords.IteratorAgeMilliseconds \
  --dimensions Name=StreamName,Value=fraud-detection-transactions-prod \
  --start-time $(date -u -d "30 minutes ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Maximum

# Check event source mapping
aws lambda list-event-source-mappings \
  --function-name fraud-detection-stream-processor-prod

# Check Lambda errors
aws logs tail /aws/lambda/fraud-detection-stream-processor-prod --since 30m | grep ERROR
```

**Solutions**:

1. **Enable event source mapping**:
   ```bash
   # Get mapping UUID
   UUID=$(aws lambda list-event-source-mappings \
     --function-name fraud-detection-stream-processor-prod \
     --query 'EventSourceMappings[0].UUID' \
     --output text)
   
   # Enable mapping
   aws lambda update-event-source-mapping \
     --uuid $UUID \
     --enabled
   ```

2. **Increase processing capacity**:
   ```bash
   # Increase Lambda concurrency
   aws lambda put-function-concurrency \
     --function-name fraud-detection-stream-processor-prod \
     --reserved-concurrent-executions 500
   
   # Increase Kinesis shards
   aws kinesis update-shard-count \
     --stream-name fraud-detection-transactions-prod \
     --target-shard-count 4 \
     --scaling-type UNIFORM_SCALING
   ```

3. **Fix Lambda errors**:
   ```bash
   # Check recent errors
   aws logs filter-pattern "ERROR" \
     --log-group-name /aws/lambda/fraud-detection-stream-processor-prod \
     --start-time $(date -u -d "1 hour ago" +%s)000
   
   # Redeploy if code issue
   ./scripts/deploy_application.sh production
   ```

### 4. High False Positive Rate

**Symptoms**:
- Many legitimate transactions flagged as fraud
- User complaints
- False positive rate > 30%

**Possible Causes**:
- Overly aggressive rules
- Incorrect risk thresholds
- Model drift
- Data quality issues

**Diagnosis**:
```bash
# Calculate false positive rate
python scripts/calculate_fp_rate.py --since 24h

# Analyze flagged transactions
python scripts/analyze_false_positives.py --since 24h

# Compare with baseline
python scripts/compare_metrics.py --baseline 7d --current 24h
```

**Solutions**:

1. **Adjust risk thresholds**:
   ```bash
   # Increase threshold for high risk
   aws ssm put-parameter \
     --name /fraud-detection/risk-threshold/high \
     --value "0.85" \
     --overwrite
   
   # Restart services to pick up new threshold
   ./scripts/restart_services.sh production
   ```

2. **Update fraud rules**:
   ```bash
   # Review and update rules
   vim fraud_rules.json
   
   # Validate rules
   python scripts/validate_rules.py fraud_rules.json
   
   # Deploy updated rules
   aws s3 cp fraud_rules.json s3://fraud-detection-models-prod/rules/current.json
   ```

3. **Retrain models**:
   ```bash
   # Retrain with recent data
   python scripts/retrain_models.py --data-range 30d --focus false-positives
   
   # Deploy new models
   ./scripts/deploy_models.sh production
   ```

### 5. Authentication Failures

**Symptoms**:
- 401 Unauthorized errors
- "Invalid or expired token" messages
- Users unable to access API

**Possible Causes**:
- Expired JWT tokens
- Invalid API keys
- IAM permission issues
- Token validation errors

**Diagnosis**:
```bash
# Check API logs
aws logs tail /aws/lambda/fraud-detection-api-prod --since 15m | grep "401\|Unauthorized"

# Verify JWT configuration
aws ssm get-parameter --name /fraud-detection/jwt/secret

# Check IAM policies
aws iam get-role-policy \
  --role-name FraudDetectionAPIRole \
  --policy-name APIAccessPolicy
```

**Solutions**:

1. **Refresh tokens**:
   ```bash
   # Get new token
   curl -X POST https://api.fraud-detection.example.com/v1/auth/token \
     -H "Content-Type: application/json" \
     -d '{"username": "user@example.com", "password": "password"}'
   ```

2. **Update JWT secret** (if compromised):
   ```bash
   # Generate new secret
   NEW_SECRET=$(openssl rand -base64 32)
   
   # Update parameter
   aws ssm put-parameter \
     --name /fraud-detection/jwt/secret \
     --value "$NEW_SECRET" \
     --overwrite
   
   # Restart services
   ./scripts/restart_services.sh production
   ```

3. **Fix IAM permissions**:
   ```bash
   # Update IAM policy
   aws iam put-role-policy \
     --role-name FraudDetectionAPIRole \
     --policy-name APIAccessPolicy \
     --policy-document file://iam_policy.json
   ```

### 6. Memory/Storage Issues

**Symptoms**:
- Out of memory errors
- DynamoDB storage warnings
- S3 bucket size growing rapidly

**Possible Causes**:
- Memory leaks
- TTL not working
- Excessive logging
- Data not being cleaned up

**Diagnosis**:
```bash
# Check Lambda memory usage
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name MemoryUtilization \
  --dimensions Name=FunctionName,Value=fraud-detection-api-prod \
  --start-time $(date -u -d "1 hour ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum

# Check DynamoDB table size
aws dynamodb describe-table \
  --table-name fraud-detection-transactions-prod \
  --query 'Table.TableSizeBytes'

# Check S3 bucket size
aws s3 ls s3://fraud-detection-audit-logs-prod --recursive --summarize
```

**Solutions**:

1. **Increase Lambda memory**:
   ```bash
   aws lambda update-function-configuration \
     --function-name fraud-detection-api-prod \
     --memory-size 3008
   ```

2. **Enable/verify TTL**:
   ```bash
   # Check TTL status
   aws dynamodb describe-time-to-live \
     --table-name fraud-detection-transactions-prod
   
   # Enable TTL if not enabled
   aws dynamodb update-time-to-live \
     --table-name fraud-detection-transactions-prod \
     --time-to-live-specification "Enabled=true,AttributeName=expiration_time"
   ```

3. **Clean up old data**:
   ```bash
   # Run cleanup script
   python scripts/cleanup_old_data.py --days 90
   
   # Apply S3 lifecycle policies
   aws s3api put-bucket-lifecycle-configuration \
     --bucket fraud-detection-audit-logs-prod \
     --lifecycle-configuration file://s3_lifecycle.json
   ```

### 7. Agent Not Responding

**Symptoms**:
- Agent timeout errors
- Missing agent results
- Agent health check fails

**Possible Causes**:
- Bedrock agent not prepared
- IAM permission issues
- Model unavailable
- Network connectivity issues

**Diagnosis**:
```bash
# Check agent status
aws bedrock-agent get-agent --agent-id $AGENT_ID

# Check agent preparation status
aws bedrock-agent get-agent --agent-id $AGENT_ID \
  --query 'agent.agentStatus'

# Check Lambda logs
aws logs tail /aws/lambda/bedrock-agent-*-prod --since 30m
```

**Solutions**:

1. **Prepare agent**:
   ```bash
   # Prepare agent
   aws bedrock-agent prepare-agent --agent-id $AGENT_ID
   
   # Wait for preparation
   aws bedrock-agent get-agent --agent-id $AGENT_ID \
     --query 'agent.agentStatus'
   ```

2. **Fix IAM permissions**:
   ```bash
   # Check permissions
   aws iam simulate-principal-policy \
     --policy-source-arn arn:aws:iam::ACCOUNT_ID:role/BedrockAgentFraudDetectionRole \
     --action-names bedrock:InvokeModel bedrock:Retrieve
   
   # Update policy if needed
   aws iam put-role-policy \
     --role-name BedrockAgentFraudDetectionRole \
     --policy-name BedrockAgentModelInvocationPolicy \
     --policy-document file://bedrock_policy.json
   ```

3. **Check model availability**:
   ```bash
   # List available models
   aws bedrock list-foundation-models --region us-east-1
   
   # Test model invocation
   aws bedrock-runtime invoke-model \
     --model-id anthropic.claude-3-sonnet-20240229-v1:0 \
     --body '{"prompt": "test", "max_tokens": 10}' \
     --region us-east-1 \
     output.json
   ```

## Error Messages

### "Rate limit exceeded"

**Meaning**: Too many requests in short time period

**Solution**:
```bash
# Implement exponential backoff
# Wait before retrying
sleep $((2 ** retry_count))

# Or increase rate limits
aws apigateway update-usage-plan \
  --usage-plan-id $PLAN_ID \
  --patch-operations op=replace,path=/throttle/rateLimit,value=2000
```

### "Resource not found"

**Meaning**: Requested resource doesn't exist

**Solution**:
```bash
# Verify resource exists
aws dynamodb get-item \
  --table-name fraud-detection-transactions-prod \
  --key '{"transaction_id": {"S": "tx_123"}}'

# Check for typos in resource IDs
# Verify correct environment (dev/staging/prod)
```

### "Insufficient permissions"

**Meaning**: IAM role lacks required permissions

**Solution**:
```bash
# Check current permissions
aws iam get-role-policy \
  --role-name YourRoleName \
  --policy-name YourPolicyName

# Add missing permissions
aws iam put-role-policy \
  --role-name YourRoleName \
  --policy-name YourPolicyName \
  --policy-document file://updated_policy.json
```

## Performance Issues

### Slow Database Queries

**Diagnosis**:
```bash
# Enable DynamoDB contributor insights
aws dynamodb update-contributor-insights \
  --table-name fraud-detection-transactions-prod \
  --contributor-insights-action ENABLE

# Check slow queries
python scripts/analyze_slow_queries.py
```

**Solutions**:
- Add appropriate indexes
- Use query instead of scan
- Implement pagination
- Enable DAX caching

### High Memory Usage

**Diagnosis**:
```bash
# Check memory metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name MemoryUtilization \
  --dimensions Name=FunctionName,Value=fraud-detection-api-prod \
  --start-time $(date -u -d "1 hour ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Maximum
```

**Solutions**:
- Increase Lambda memory
- Optimize data structures
- Implement streaming for large datasets
- Clear unused variables

## Getting Help

### Self-Service Resources

1. **Documentation**: Check docs/ directory
2. **Logs**: Review CloudWatch Logs
3. **Metrics**: Check CloudWatch Dashboards
4. **Status Page**: https://status.fraud-detection.example.com

### Support Channels

1. **Slack**: #fraud-detection-support
2. **Email**: support@fraud-detection.example.com
3. **PagerDuty**: For critical issues
4. **Internal Wiki**: https://wiki.fraud-detection.example.com

### Escalation

If issue persists after troubleshooting:
1. Document what you've tried
2. Gather relevant logs and metrics
3. Follow escalation procedures in Operations Runbook
4. Contact on-call engineer

## Useful Scripts

```bash
# Quick health check
./scripts/quick_health_check.sh

# Diagnose issues
./scripts/diagnose_system.sh

# Generate debug report
./scripts/generate_debug_report.sh

# Check all metrics
python scripts/check_all_metrics.py

# Analyze recent errors
python scripts/analyze_errors.py --since 1h
```

## Additional Resources

- [Operations Runbook](OPERATIONS_RUNBOOK.md)
- [Architecture Documentation](ARCHITECTURE.md)
- [API Reference](API_REFERENCE.md)
- [AWS Documentation](https://docs.aws.amazon.com/)
