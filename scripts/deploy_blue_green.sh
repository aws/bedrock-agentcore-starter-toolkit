#!/bin/bash
"""
Blue-Green Deployment Script

Implements blue-green deployment strategy for zero-downtime deployments.
"""

set -e

# Configuration
ENVIRONMENT=${1:-dev}
REGION=${AWS_REGION:-us-east-1}
BLUE_STACK="fraud-detection-blue-${ENVIRONMENT}"
GREEN_STACK="fraud-detection-green-${ENVIRONMENT}"
ACTIVE_STACK_PARAM="/fraud-detection/${ENVIRONMENT}/active-stack"

echo "========================================="
echo "Blue-Green Deployment"
echo "Environment: ${ENVIRONMENT}"
echo "Region: ${REGION}"
echo "========================================="

# Get current active stack
CURRENT_ACTIVE=$(aws ssm get-parameter \
  --name "${ACTIVE_STACK_PARAM}" \
  --query 'Parameter.Value' \
  --output text \
  --region "${REGION}" 2>/dev/null || echo "blue")

echo "Current active stack: ${CURRENT_ACTIVE}"

# Determine target stack
if [ "${CURRENT_ACTIVE}" == "blue" ]; then
  TARGET_STACK="${GREEN_STACK}"
  TARGET_COLOR="green"
else
  TARGET_STACK="${BLUE_STACK}"
  TARGET_COLOR="blue"
fi

echo "Deploying to: ${TARGET_COLOR} stack"

# Deploy to target stack
echo "Step 1: Deploying infrastructure to ${TARGET_COLOR} stack..."
cd aws_infrastructure
python deploy_full_infrastructure.py \
  --environment "${ENVIRONMENT}" \
  --region "${REGION}" \
  --stack-suffix "${TARGET_COLOR}"

# Deploy Lambda functions
echo "Step 2: Deploying Lambda functions..."
aws lambda update-function-code \
  --function-name "fraud-detection-stream-processor-${ENVIRONMENT}-${TARGET_COLOR}" \
  --zip-file fileb://dist/lambda/stream_processor.zip \
  --region "${REGION}"

aws lambda update-function-code \
  --function-name "fraud-detection-alert-handler-${ENVIRONMENT}-${TARGET_COLOR}" \
  --zip-file fileb://dist/lambda/alert_handler.zip \
  --region "${REGION}"

# Wait for functions to be ready
echo "Step 3: Waiting for Lambda functions to be ready..."
aws lambda wait function-updated \
  --function-name "fraud-detection-stream-processor-${ENVIRONMENT}-${TARGET_COLOR}" \
  --region "${REGION}"

aws lambda wait function-updated \
  --function-name "fraud-detection-alert-handler-${ENVIRONMENT}-${TARGET_COLOR}" \
  --region "${REGION}"

# Run health checks
echo "Step 4: Running health checks on ${TARGET_COLOR} stack..."
python ../scripts/health_check.py \
  --environment "${ENVIRONMENT}" \
  --stack "${TARGET_COLOR}"

if [ $? -ne 0 ]; then
  echo "ERROR: Health checks failed on ${TARGET_COLOR} stack"
  exit 1
fi

# Run smoke tests
echo "Step 5: Running smoke tests..."
python ../tests/run_all_tests.py \
  --quick \
  --environment "${ENVIRONMENT}" \
  --stack "${TARGET_COLOR}"

if [ $? -ne 0 ]; then
  echo "ERROR: Smoke tests failed on ${TARGET_COLOR} stack"
  exit 1
fi

# Switch traffic to new stack
echo "Step 6: Switching traffic to ${TARGET_COLOR} stack..."

# Update API Gateway or Load Balancer to point to new stack
# This depends on your specific setup
# Example: Update Route53 weighted routing

# Update active stack parameter
aws ssm put-parameter \
  --name "${ACTIVE_STACK_PARAM}" \
  --value "${TARGET_COLOR}" \
  --overwrite \
  --region "${REGION}"

echo "Step 7: Monitoring new stack for 5 minutes..."
sleep 300

# Final health check
python ../scripts/health_check.py \
  --environment "${ENVIRONMENT}" \
  --stack "${TARGET_COLOR}"

if [ $? -ne 0 ]; then
  echo "ERROR: Health checks failed after traffic switch"
  echo "Rolling back..."
  
  # Rollback
  aws ssm put-parameter \
    --name "${ACTIVE_STACK_PARAM}" \
    --value "${CURRENT_ACTIVE}" \
    --overwrite \
    --region "${REGION}"
  
  exit 1
fi

echo "========================================="
echo "Deployment successful!"
echo "Active stack: ${TARGET_COLOR}"
echo "Previous stack (${CURRENT_ACTIVE}) is still running for rollback"
echo "========================================="

# Optional: Decommission old stack after verification period
echo "To decommission old ${CURRENT_ACTIVE} stack, run:"
echo "./scripts/decommission_stack.sh ${ENVIRONMENT} ${CURRENT_ACTIVE}"
