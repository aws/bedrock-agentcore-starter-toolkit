# Operations Runbook

## Overview

This runbook provides step-by-step procedures for common operational tasks, incident response, and troubleshooting for the Fraud Detection System.

## Table of Contents

1. [System Monitoring](#system-monitoring)
2. [Common Operations](#common-operations)
3. [Incident Response](#incident-response)
4. [Troubleshooting](#troubleshooting)
5. [Maintenance Procedures](#maintenance-procedures)
6. [Escalation Procedures](#escalation-procedures)

## System Monitoring

### Daily Health Checks

**Frequency**: Every morning

**Steps**:
1. Check CloudWatch Dashboard
   ```bash
   # Open dashboard
   open https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=fraud-detection-prod
   ```

2. Verify Key Metrics:
   - ✓ Throughput: Should be within normal range (500-2000 TPS)
   - ✓ Response Time: Avg < 500ms, P95 < 1s, P99 < 2s
   - ✓ Error Rate: < 0.1%
   - ✓ Decision Accuracy: > 85%

3. Check Active Alarms:
   ```bash
   aws cloudwatch describe-alarms --state-value ALARM --region us-east-1
   ```

4. Review Recent Errors:
   ```bash
   aws logs tail /aws/lambda/fraud-detection-stream-processor-prod --since 1h
   ```

5. Verify Agent Health:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" https://api.fraud-detection.example.com/v1/health
   ```

**Expected Output**:
```json
{
  "status": "healthy",
  "components": {
    "api": "healthy",
    "database": "healthy",
    "agents": "healthy",
    "bedrock": "healthy"
  }
}
```

### Weekly Performance Review

**Frequency**: Every Monday

**Steps**:
1. Generate Weekly Report:
   ```bash
   python scripts/generate_weekly_report.py --week last
   ```

2. Review Metrics:
   - Transaction volume trends
   - Fraud detection rate
   - False positive/negative rates
   - System performance trends

3. Identify Anomalies:
   - Unusual spikes in traffic
   - Changes in fraud patterns
   - Performance degradation

4. Document Findings:
   - Update operations log
   - Share with team
   - Plan improvements

## Common Operations

### 1. Deploying New Version

**When**: After code changes are merged

**Steps**:

1. **Pre-Deployment Checks**:
   ```bash
   # Run tests
   python tests/run_all_tests.py
   
   # Check current system health
   curl https://api.fraud-detection.example.com/v1/health
   ```

2. **Deploy to Staging**:
   ```bash
   # Deploy infrastructure
   cd aws_infrastructure
   python deploy_full_infrastructure.py --environment staging
   
   # Deploy application code
   ./scripts/deploy_application.sh staging
   ```

3. **Verify Staging**:
   ```bash
   # Run smoke tests
   python tests/run_all_tests.py --quick --environment staging
   
   # Manual verification
   curl https://staging-api.fraud-detection.example.com/v1/health
   ```

4. **Deploy to Production**:
   ```bash
   # Create backup
   ./scripts/backup_production.sh
   
   # Deploy with blue-green strategy
   ./scripts/deploy_application.sh production --strategy blue-green
   ```

5. **Post-Deployment Verification**:
   ```bash
   # Check health
   curl https://api.fraud-detection.example.com/v1/health
   
   # Monitor metrics for 15 minutes
   watch -n 30 'aws cloudwatch get-metric-statistics --namespace FraudDetection --metric-name ErrorRate --start-time $(date -u -d "15 minutes ago" +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 300 --statistics Average'
   ```

6. **Rollback if Needed**:
   ```bash
   # If issues detected
   ./scripts/rollback_deployment.sh production
   ```

### 2. Scaling System Resources

**When**: Anticipating high traffic or performance issues

**Steps**:

1. **Assess Current Capacity**:
   ```bash
   # Check current metrics
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name ConcurrentExecutions \
     --start-time $(date -u -d "1 hour ago" +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Maximum
   ```

2. **Scale Lambda Concurrency**:
   ```bash
   # Increase reserved concurrency
   aws lambda put-function-concurrency \
     --function-name fraud-detection-stream-processor-prod \
     --reserved-concurrent-executions 500
   ```

3. **Scale DynamoDB**:
   ```bash
   # Switch to on-demand if needed
   aws dynamodb update-table \
     --table-name fraud-detection-transactions-prod \
     --billing-mode PAY_PER_REQUEST
   ```

4. **Scale Kinesis**:
   ```bash
   # Increase shard count
   aws kinesis update-shard-count \
     --stream-name fraud-detection-transactions-prod \
     --target-shard-count 4 \
     --scaling-type UNIFORM_SCALING
   ```

5. **Monitor Impact**:
   ```bash
   # Watch metrics for 30 minutes
   watch -n 60 './scripts/check_system_metrics.sh'
   ```

### 3. Updating Fraud Detection Rules

**When**: New fraud patterns identified

**Steps**:

1. **Backup Current Rules**:
   ```bash
   aws s3 cp s3://fraud-detection-models-prod/rules/current.json \
     s3://fraud-detection-models-prod/rules/backup-$(date +%Y%m%d).json
   ```

2. **Update Rules**:
   ```bash
   # Edit rules file
   vim fraud_rules.json
   
   # Validate rules
   python scripts/validate_rules.py fraud_rules.json
   ```

3. **Deploy to Staging**:
   ```bash
   aws s3 cp fraud_rules.json s3://fraud-detection-models-staging/rules/current.json
   ```

4. **Test in Staging**:
   ```bash
   # Run test transactions
   python scripts/test_fraud_rules.py --environment staging
   ```

5. **Deploy to Production**:
   ```bash
   aws s3 cp fraud_rules.json s3://fraud-detection-models-prod/rules/current.json
   
   # Trigger rule reload
   aws lambda invoke \
     --function-name fraud-detection-reload-rules-prod \
     --payload '{"action": "reload"}' \
     response.json
   ```

6. **Monitor Impact**:
   ```bash
   # Watch false positive/negative rates
   python scripts/monitor_rule_impact.py --duration 1h
   ```

### 4. Managing User Profiles

**When**: User reports issues or profile needs update

**Steps**:

1. **Retrieve User Profile**:
   ```bash
   aws dynamodb get-item \
     --table-name fraud-detection-user-profiles-prod \
     --key '{"user_id": {"S": "user_123"}}'
   ```

2. **Update Profile**:
   ```bash
   # Update typical locations
   aws dynamodb update-item \
     --table-name fraud-detection-user-profiles-prod \
     --key '{"user_id": {"S": "user_123"}}' \
     --update-expression "SET typical_locations = :locs" \
     --expression-attribute-values '{":locs": {"L": [{"S": "New York"}, {"S": "Boston"}]}}'
   ```

3. **Reset Risk Score** (if needed):
   ```bash
   aws dynamodb update-item \
     --table-name fraud-detection-user-profiles-prod \
     --key '{"user_id": {"S": "user_123"}}' \
     --update-expression "SET risk_score = :score" \
     --expression-attribute-values '{":score": {"N": "0.1"}}'
   ```

4. **Verify Update**:
   ```bash
   curl -H "Authorization: Bearer $TOKEN" \
     https://api.fraud-detection.example.com/v1/users/user_123/profile
   ```

## Incident Response

### High Error Rate Alert

**Trigger**: Error rate > 1% for 5 minutes

**Severity**: P1 (Critical)

**Response Steps**:

1. **Acknowledge Alert** (< 5 minutes):
   ```bash
   # Acknowledge in PagerDuty/Slack
   # Check CloudWatch dashboard
   ```

2. **Assess Impact** (< 10 minutes):
   ```bash
   # Check error logs
   aws logs tail /aws/lambda/fraud-detection-stream-processor-prod --since 15m | grep ERROR
   
   # Check affected users
   aws logs filter-pattern "ERROR" --log-group-name /aws/lambda/fraud-detection-stream-processor-prod --start-time $(date -u -d "15 minutes ago" +%s)000
   ```

3. **Identify Root Cause** (< 20 minutes):
   - Check recent deployments
   - Review X-Ray traces
   - Check external service status
   - Review CloudWatch metrics

4. **Mitigate** (< 30 minutes):
   ```bash
   # Option 1: Rollback if recent deployment
   ./scripts/rollback_deployment.sh production
   
   # Option 2: Increase resources if capacity issue
   aws lambda put-function-concurrency \
     --function-name fraud-detection-stream-processor-prod \
     --reserved-concurrent-executions 1000
   
   # Option 3: Enable circuit breaker if external service issue
   aws ssm put-parameter \
     --name /fraud-detection/circuit-breaker/enabled \
     --value "true" \
     --overwrite
   ```

5. **Verify Resolution** (< 45 minutes):
   ```bash
   # Monitor error rate
   watch -n 30 './scripts/check_error_rate.sh'
   ```

6. **Post-Incident** (< 24 hours):
   - Write incident report
   - Identify preventive measures
   - Update runbook
   - Schedule post-mortem

### High Latency Alert

**Trigger**: P95 response time > 2s for 10 minutes

**Severity**: P2 (High)

**Response Steps**:

1. **Check System Load**:
   ```bash
   # Check Lambda metrics
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name Duration \
     --dimensions Name=FunctionName,Value=fraud-detection-stream-processor-prod \
     --start-time $(date -u -d "30 minutes ago" +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Average,Maximum
   ```

2. **Identify Bottleneck**:
   - Check X-Ray service map
   - Review slow queries in DynamoDB
   - Check external API latency
   - Review agent processing times

3. **Optimize**:
   ```bash
   # Increase Lambda memory (improves CPU)
   aws lambda update-function-configuration \
     --function-name fraud-detection-stream-processor-prod \
     --memory-size 1024
   
   # Enable DynamoDB DAX if not already
   ./scripts/enable_dax.sh production
   
   # Increase cache TTL
   aws ssm put-parameter \
     --name /fraud-detection/cache/ttl \
     --value "600" \
     --overwrite
   ```

4. **Monitor Improvement**:
   ```bash
   watch -n 60 './scripts/check_latency.sh'
   ```

### Fraud Detection Accuracy Drop

**Trigger**: Decision accuracy < 80% for 1 hour

**Severity**: P2 (High)

**Response Steps**:

1. **Analyze Recent Decisions**:
   ```bash
   # Get recent decisions
   python scripts/analyze_decisions.py --since 1h
   ```

2. **Check for Pattern Changes**:
   ```bash
   # Compare with historical patterns
   python scripts/compare_fraud_patterns.py --baseline 7d --current 1h
   ```

3. **Review False Positives/Negatives**:
   ```bash
   # Get false positive rate
   python scripts/calculate_fp_rate.py --since 1h
   
   # Get false negative rate
   python scripts/calculate_fn_rate.py --since 1h
   ```

4. **Adjust Thresholds** (if needed):
   ```bash
   # Update risk thresholds
   aws ssm put-parameter \
     --name /fraud-detection/risk-threshold/high \
     --value "0.75" \
     --overwrite
   ```

5. **Retrain Models** (if needed):
   ```bash
   # Trigger model retraining
   python scripts/retrain_models.py --data-range 30d
   ```

### Database Connection Issues

**Trigger**: DynamoDB throttling or connection errors

**Severity**: P1 (Critical)

**Response Steps**:

1. **Check DynamoDB Metrics**:
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/DynamoDB \
     --metric-name UserErrors \
     --dimensions Name=TableName,Value=fraud-detection-transactions-prod \
     --start-time $(date -u -d "30 minutes ago" +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Sum
   ```

2. **Increase Capacity**:
   ```bash
   # Switch to on-demand
   aws dynamodb update-table \
     --table-name fraud-detection-transactions-prod \
     --billing-mode PAY_PER_REQUEST
   ```

3. **Enable Connection Pooling**:
   ```bash
   # Update Lambda environment variable
   aws lambda update-function-configuration \
     --function-name fraud-detection-stream-processor-prod \
     --environment Variables={DB_POOL_SIZE=50}
   ```

4. **Monitor Recovery**:
   ```bash
   watch -n 30 'aws cloudwatch get-metric-statistics --namespace AWS/DynamoDB --metric-name UserErrors --dimensions Name=TableName,Value=fraud-detection-transactions-prod --start-time $(date -u -d "5 minutes ago" +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 60 --statistics Sum'
   ```

## Troubleshooting

### Issue: Transactions Not Processing

**Symptoms**:
- Transactions stuck in queue
- No responses from API
- Kinesis stream backlog growing

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

# Check Lambda errors
aws logs tail /aws/lambda/fraud-detection-stream-processor-prod --since 30m | grep ERROR
```

**Resolution**:
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

### Issue: High False Positive Rate

**Symptoms**:
- Many legitimate transactions flagged
- User complaints
- False positive rate > 30%

**Diagnosis**:
```bash
# Analyze recent decisions
python scripts/analyze_false_positives.py --since 24h

# Check rule changes
git log --since="24 hours ago" -- fraud_rules.json
```

**Resolution**:
```bash
# Adjust risk thresholds
aws ssm put-parameter \
  --name /fraud-detection/risk-threshold/high \
  --value "0.85" \
  --overwrite

# Update specific rules
python scripts/update_fraud_rules.py --rule velocity_check --threshold 10

# Retrain models with recent data
python scripts/retrain_models.py --focus false-positives
```

### Issue: Agent Not Responding

**Symptoms**:
- Timeout errors
- Agent health check fails
- Missing agent results

**Diagnosis**:
```bash
# Check agent status
curl -H "Authorization: Bearer $TOKEN" \
  https://api.fraud-detection.example.com/v1/agents/status

# Check Bedrock agent
aws bedrock-agent get-agent --agent-id $AGENT_ID

# Check Lambda logs
aws logs tail /aws/lambda/bedrock-agent-*-prod --since 30m
```

**Resolution**:
```bash
# Restart agent (prepare again)
aws bedrock-agent prepare-agent --agent-id $AGENT_ID

# Increase timeout
aws lambda update-function-configuration \
  --function-name fraud-detection-stream-processor-prod \
  --timeout 120

# Check and fix IAM permissions
aws iam get-role-policy \
  --role-name BedrockAgentFraudDetectionRole \
  --policy-name BedrockAgentModelInvocationPolicy
```

## Maintenance Procedures

### Monthly Database Cleanup

**When**: First Sunday of each month

**Steps**:
```bash
# 1. Backup data
./scripts/backup_dynamodb.sh production

# 2. Clean expired records (TTL should handle this, but verify)
python scripts/verify_ttl_cleanup.py

# 3. Optimize indexes
python scripts/optimize_dynamodb_indexes.py

# 4. Verify data integrity
python scripts/verify_data_integrity.py
```

### Quarterly Security Audit

**When**: Every quarter

**Steps**:
```bash
# 1. Review IAM policies
aws iam get-account-authorization-details > iam_audit.json
python scripts/audit_iam_policies.py iam_audit.json

# 2. Check for unused resources
python scripts/find_unused_resources.py

# 3. Review CloudTrail logs
python scripts/audit_cloudtrail.py --days 90

# 4. Update dependencies
pip list --outdated
npm outdated

# 5. Run security scan
./scripts/run_security_scan.sh
```

## Escalation Procedures

### Escalation Levels

**Level 1 - On-Call Engineer**:
- Initial response
- Basic troubleshooting
- Follow runbook procedures

**Level 2 - Senior Engineer**:
- Complex issues
- Architecture decisions
- Performance optimization

**Level 3 - Engineering Lead**:
- Critical system failures
- Major incidents
- Business impact decisions

**Level 4 - CTO/VP Engineering**:
- Company-wide impact
- Security breaches
- Major outages

### Escalation Criteria

**Escalate to Level 2 if**:
- Issue not resolved in 30 minutes
- Runbook procedures don't work
- Root cause unclear
- Multiple systems affected

**Escalate to Level 3 if**:
- Issue not resolved in 1 hour
- Major business impact
- Data loss or corruption
- Security incident

**Escalate to Level 4 if**:
- Complete system outage
- Data breach
- Regulatory compliance issue
- Major financial impact

### Contact Information

```
Level 1: on-call@fraud-detection.example.com
Level 2: senior-eng@fraud-detection.example.com
Level 3: eng-lead@fraud-detection.example.com
Level 4: cto@fraud-detection.example.com

PagerDuty: https://fraud-detection.pagerduty.com
Slack: #fraud-detection-ops
Status Page: https://status.fraud-detection.example.com
```

## Useful Commands

### Quick Health Check
```bash
./scripts/quick_health_check.sh
```

### View Recent Errors
```bash
aws logs tail /aws/lambda/fraud-detection-stream-processor-prod --since 1h | grep ERROR
```

### Check System Metrics
```bash
python scripts/check_system_metrics.py
```

### Generate Report
```bash
python scripts/generate_ops_report.py --period daily
```

### Backup System
```bash
./scripts/backup_all.sh production
```

## Additional Resources

- [Architecture Documentation](ARCHITECTURE.md)
- [API Reference](API_REFERENCE.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)
- [AWS Documentation](https://docs.aws.amazon.com/)
- [Internal Wiki](https://wiki.fraud-detection.example.com)
