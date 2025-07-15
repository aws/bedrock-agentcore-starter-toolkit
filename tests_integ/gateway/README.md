# Bedrock AgentCore Gateway Testing

This directory contains integration tests for the Bedrock AgentCore Gateway functionality. Since the tests create real AWS resources, proper setup is required before running them.

## Prerequisites

Before running the tests, you need:

1. AWS credentials with appropriate permissions
2. An IAM execution role for the Gateway
3. A Lambda function for testing Gateway targets

### 1. IAM Execution Role Requirements

Create an IAM role with:
- **Trust Relationship:** Trust the Gateway beta account
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "AWS": "arn:aws:iam::996756280381:root"  // Beta account
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }
  ```
- **Permissions:** Include these policies
  ```json
  {
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "bedrock-agentcore:*",
          "lambda:InvokeFunction",
          "s3:GetObject",
          "iam:PassRole"
        ],
        "Resource": "*"
      }
    ]
  }
  ```

### 2. Lambda Function Requirements

Create a simple Lambda function in Python with this code:

```python
import json

def lambda_handler(event, context):
    # Extract tool name from context if available
    tool_name = "unknown"
    if hasattr(context, 'client_context') and context.client_context:
        if hasattr(context.client_context, 'custom'):
            tool_name = context.client_context.custom.get('bedrockAgentCoreToolName', 'unknown')

    # Log request details for debugging
    print(f"Received event: {json.dumps(event)}")
    print(f"Tool name: {tool_name}")

    # Return response based on tool name
    if tool_name == 'get_weather':
        return {
            'statusCode': 200,
            'body': json.dumps({
                'location': event.get('location', 'Unknown'),
                'temperature': '72°F',
                'conditions': 'Sunny'
            })
        }
    elif tool_name == 'checkIdentity':
        # Try to get caller identity
        try:
            import boto3
            sts = boto3.client('sts')
            identity = sts.get_caller_identity()
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Identity check',
                    'caller_arn': identity['Arn'],
                    'account': identity['Account']
                })
            }
        except Exception as e:
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'message': 'Could not get caller identity',
                    'error': str(e)
                })
            }
    else:
        return {
            'statusCode': 200,
            'body': json.dumps({'message': f'Invoked tool: {tool_name}'})
        }
```

## Setting Up Environment Variables

Before running the tests, set the following environment variables:

```bash
# Required for all tests
export GATEWAY_EXECUTION_ROLE_ARN="arn:aws:iam::<your-account>:role/<your-role-name>"
export GATEWAY_LAMBDA_ARN="arn:aws:lambda:<region>:<your-account>:function:<your-function-name>"

# Optional - will be set by test_gateway_cognito.py
export TEST_COGNITO_CLIENT_ID=""
export TEST_COGNITO_CLIENT_SECRET=""
export TEST_COGNITO_TOKEN_ENDPOINT=""
export TEST_COGNITO_SCOPE=""
```

## Test Sequence

Run the tests in this order:

1. **test_gateway_cognito.py** - Creates a Gateway with Cognito OAuth and saves credentials
2. **test_cognito_token.py** - Tests token acquisition from Cognito
3. **test_egress_auth.py** - Tests Gateway's ability to invoke backend services

## Running Tests

```bash
# Step 1: Set up environment variables as described above

# Step 2: Run test_gateway_cognito.py to create Gateway and Cognito resources
python tests_integ/gateway/test_gateway_cognito.py

# Step 3: Extract Cognito credentials from output or gateway_info.json
# The test will save credentials to a file called gateway_info.json

# Step 4: Run token test
python tests_integ/gateway/test_cognito_token.py

# Step 5: Test egress authentication
python tests_integ/gateway/test_egress_auth.py
```
