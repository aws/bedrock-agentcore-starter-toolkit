#!/bin/bash
"""
Rollback Deployment Script

Rolls back to previous deployment in case of issues.
"""

set -e

# Configuration
ENVIRONMENT=${1:-dev}
REGION=${AWS_REGION:-us-east-1}
ACTIVE_STACK_PARAM="/fraud-detection/${ENVIRONMENT}/active-stack"

echo "========================================="
echo "Rollback Deployment"
echo "Environment: ${ENVIRONMENT}"
echo "Region: ${REGION}"
echo "========================================="

# Get current active stack
CURRENT_ACTIVE=$(aws ssm get-parameter \
  --name "${ACTIVE_STACK_PARAM}" \
  --query 'Parameter.Value' \
  --output text \
  --region "${REGION}")

echo "Current active stack: ${CURRENT_ACTIVE}"

# Determine previous stack
if [ "${CURRENT_ACTIVE}" == "blue" ]; then
  PREVIOUS_STACK="green"
else
  PREVIOUS_STACK="blue"
fi

echo "Rolling back to: ${PREVIOUS_STACK} stack"

# Verify previous stack exists and is healthy
echo "Step 1: Verifying ${PREVIOUS_STACK} stack health..."
python scripts/health_check.py \
  --environment "${ENVIRONMENT}" \
  --stack "${PREVIOUS_STACK}"

if [ $? -ne 0 ]; then
  echo "ERROR: Previous ${PREVIOUS_STACK} stack is not healthy"
  echo "Cannot rollback safely"
  exit 1
fi

# Switch traffic back to previous stack
echo "Step 2: Switching traffic to ${PREVIOUS_STACK} stack..."

# Update active stack parameter
aws ssm put-parameter \
  --name "${ACTIVE_STACK_PARAM}" \
  --value "${PREVIOUS_STACK}" \
  --overwrite \
  --region "${REGION}"

echo "Step 3: Verifying rollback..."
sleep 30

# Health check after rollback
python scripts/health_check.py \
  --environment "${ENVIRONMENT}" \
  --stack "${PREVIOUS_STACK}"

if [ $? -ne 0 ]; then
  echo "ERROR: Health checks failed after rollback"
  echo "Manual intervention required"
  exit 1
fi

# Run smoke tests
echo "Step 4: Running smoke tests..."
python tests/run_all_tests.py \
  --quick \
  --environment "${ENVIRONMENT}" \
  --stack "${PREVIOUS_STACK}"

if [ $? -ne 0 ]; then
  echo "WARNING: Smoke tests failed after rollback"
  echo "System is running but may have issues"
fi

echo "========================================="
echo "Rollback successful!"
echo "Active stack: ${PREVIOUS_STACK}"
echo "Failed stack (${CURRENT_ACTIVE}) is still running for investigation"
echo "========================================="

# Send notification
python scripts/send_notification.py \
  --type "rollback" \
  --environment "${ENVIRONMENT}" \
  --from-stack "${CURRENT_ACTIVE}" \
  --to-stack "${PREVIOUS_STACK}"

echo "To investigate failed ${CURRENT_ACTIVE} stack:"
echo "  aws logs tail /aws/lambda/fraud-detection-stream-processor-${ENVIRONMENT}-${CURRENT_ACTIVE} --follow"
echo ""
echo "To decommission failed ${CURRENT_ACTIVE} stack after investigation:"
echo "  ./scripts/decommission_stack.sh ${ENVIRONMENT} ${CURRENT_ACTIVE}"
