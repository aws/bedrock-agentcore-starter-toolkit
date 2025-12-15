# Policy Integration Examples

This guide demonstrates practical patterns for integrating Policy with AgentCore Gateway, including complete working examples, common policy patterns, and best practices.

## Complete Example: Refund Processing System

This end-to-end example shows how to create a policy-protected refund processing system.

**Important: Action Name Format**

Action names in Cedar policies use the format `TargetName___tool_name` with **three underscores** (`___`):
- Format: `AgentCore::Action::"<TargetName>___<tool_name>"`
- Example: `AgentCore::Action::"RefundTarget___process_refund"`
- The target name from your gateway and the tool name are separated by triple underscores

### Step 1: Create Policy Engine

```python
from bedrock_agentcore_starter_toolkit.operations.policy import PolicyClient

# Initialize the policy client
policy_client = PolicyClient(region_name='us-west-2')

# Create a policy engine
policy_engine = policy_client.create_or_get_policy_engine(
    name='RefundPolicyEngine',
    description='Policy engine for refund processing authorization'
)

print(f"Policy Engine ARN: {policy_engine['policyEngineArn']}")
```

### Step 2: Create Cedar Policies

```python
# Policy 1: Allow refund-agent to process refunds under $500
refund_policy = """
permit(
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"RefundTarget___process_refund",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/refund-gateway"
)
when {
  principal.hasTag("username") &&
  principal.getTag("username") == "refund-agent" &&
  context.input.amount < 500
};
"""

policy_client.create_policy(
    policy_engine_id=policy_engine['policyEngineId'],
    name='RefundUnder500Policy',
    definition={'cedar': {'statement': refund_policy}},
    validation_mode='FAIL_ON_ANY_FINDINGS'
)

# Policy 2: Emergency shutdown - forbid all refunds
emergency_policy = """
forbid(
  principal,
  action == AgentCore::Action::"RefundTarget___process_refund",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/refund-gateway"
);
"""

# Note: This policy is created but can be enabled/disabled as needed
```

### Step 3: Create Gateway with Policy Engine

```python
from bedrock_agentcore_starter_toolkit.operations.gateway.client import GatewayClient
import json

gateway_client = GatewayClient(region_name='us-west-2')

# Define Lambda refund tool
lambda_config = {
    "arn": "arn:aws:lambda:us-west-2:123456789012:function:RefundProcessor",
    "tools": [
        {
            "name": "process_refund",
            "description": "Process customer refund",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "orderId": {"type": "string"},
                    "amount": {"type": "integer"},
                    "reason": {"type": "string"}
                },
                "required": ["orderId", "amount"]
            }
        }
    ]
}

# Create Gateway with OAuth and Policy Engine
cognito = gateway_client.create_oauth_authorizer_with_cognito("refund-processor")

# Create the Gateway
gateway = gateway_client.create_mcp_gateway(
    name="refund-gateway",
    role_arn=None,  # Auto-creates IAM role
    authorizer_config=cognito['authorizer_config'],
    enable_semantic_search=False
)

# Add Lambda target
lambda_target = gateway_client.create_mcp_gateway_target(
    gateway=gateway,
    name="RefundTool",
    target_type="lambda",
    target_payload={
        "lambdaArn": "arn:aws:lambda:us-west-2:123456789012:function:RefundProcessor",
        "toolSchema": {
            "inlinePayload": [
                {
                    "name": "process_refund",
                    "description": "Process customer refund",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "orderId": {"type": "string"},
                            "amount": {"type": "integer"},
                            "reason": {"type": "string"}
                        },
                        "required": ["orderId", "amount"]
                    }
                }
            ]
        }
    },
    credentials=None
)

# Attach Policy Engine to Gateway
gateway_client.update_gateway_policy_engine(
    gateway_identifier=gateway["gatewayId"],
    policy_engine_arn=policy_engine['policyEngineArn'],
    mode="ENFORCE"
)

print(f"Gateway URL: {gateway['gatewayUrl']}")
```

### Step 4: Test the Policy

```python
import httpx
import asyncio

async def test_refund_policy():
    # Get OAuth token (from Cognito)
    token = gateway_client.get_access_token_for_cognito(cognito['client_info'])

    gateway_url = gateway['gatewayUrl']

    # Test 1: Valid refund (under $500)
    response1 = await httpx.AsyncClient().post(
        gateway_url,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "RefundTool__process_refund",
                "arguments": {
                    "orderId": "12345",
                    "amount": 450,
                    "reason": "Defective product"
                }
            }
        }
    )
    print(f"Test 1 (amount=450): {response1.json()}")  # Should ALLOW

    # Test 2: Invalid refund (over $500)
    response2 = await httpx.AsyncClient().post(
        gateway_url,
        headers={"Authorization": f"Bearer {token}"},
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "RefundTool__process_refund",
                "arguments": {
                    "orderId": "12346",
                    "amount": 750,
                    "reason": "Defective product"
                }
            }
        }
    )
    print(f"Test 2 (amount=750): {response2.json()}")  # Should DENY

asyncio.run(test_refund_policy())
```

## Common Policy Patterns

### Amount-Based Restrictions

Limit operations based on monetary amounts:

```python
# Natural language
nl_policy = "Allow users with scope payment:process to transfer funds when the amount is less than $10,000"

# Converts to Cedar
cedar_policy = """
permit(
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"PaymentTarget___transfer_funds",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/payment"
)
when {
  principal.hasTag("scope") &&
  principal.getTag("scope") like "*payment:process*" &&
  context.input.amount < 10000
};
"""
```

### User Tier-Based Access

Different limits for different user tiers:

```python
# Premium users: transfers up to $50,000
premium_policy = """
permit(
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"PaymentTarget___transfer_funds",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/payment"
)
when {
  principal.hasTag("tier") &&
  principal.getTag("tier") == "premium" &&
  context.input.amount < 50000
};
"""

# Standard users: transfers up to $10,000
standard_policy = """
permit(
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"PaymentTarget___transfer_funds",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/payment"
)
when {
  principal.hasTag("tier") &&
  principal.getTag("tier") == "standard" &&
  context.input.amount < 10000
};
"""
```

### Regional Restrictions

Restrict operations to specific regions:

```python
# Allow only for US, CA, UK regions
regional_policy = """
permit(
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"ShippingTarget___calculate_rate",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/shipping"
)
when {
  context.input has region &&
  ["US", "CA", "UK"].contains(context.input.region)
};
"""
```

### Role-Based Access Control

Control access based on user roles:

```python
# Allow managers to approve high-value decisions
manager_policy = """
permit(
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"DecisionTarget___approve_decision",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/decision"
)
when {
  principal.hasTag("role") &&
  ["manager", "director"].contains(principal.getTag("role")) &&
  context.input.amount > 100000
};
"""
```

### Required Field Validation

Enforce that optional parameters are provided:

```python
# Require description for all claims
required_description_policy = """
forbid(
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"InsuranceTarget___file_claim",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/insurance"
)
unless {
  context.input has description
};
"""
```

### Emergency Shutdown Patterns

#### Disable All Tools

```python
emergency_shutdown = """
forbid(
  principal,
  action,
  resource
);
"""
```

#### Disable Specific Tool

```python
disable_tool = """
forbid(
  principal,
  action == AgentCore::Action::"PaymentTarget___transfer_funds",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/payment"
);
"""
```

#### Block Specific User

```python
block_user = """
forbid(
  principal is AgentCore::OAuthUser,
  action,
  resource
)
when {
  principal.hasTag("username") &&
  principal.getTag("username") == "suspended-user"
};
"""
```

## Natural Language Policy Authoring

### Using the Policy Authoring Service

```python
# Generate Cedar policy from natural language (automatic polling & fetching)
# Note: name must match pattern ^[A-Za-z][A-Za-z0-9_]*$ (use underscores, not hyphens)
result = policy_client.generate_policy(
    policy_engine_id=policy_engine['policyEngineId'],
    name='refund_policy',  # Use underscores, not hyphens
    resource={'arn': gateway['gatewayArn']},
    content={'rawText': 'Allow refunds for amounts less than $500'},
    fetch_assets=True  # Automatically fetches generated policies
)

# Display generated Cedar policies
for policy_asset in result.get('generatedPolicies', []):
    cedar_statement = policy_asset['definition']['cedar']['statement']
    print(f"Generated Cedar Policy:\n{cedar_statement}")
```

### Natural Language Examples

```python
# Example 1: Simple amount restriction
nl1 = "Allow users to process payments when the amount is less than $1000"

# Example 2: Role and amount combined
nl2 = "Allow users with role manager to approve expenses when the amount exceeds $5000"

# Example 3: Regional restrictions
nl3 = "Allow all users to ship packages when the destination country is US, CA, or UK"

# Example 4: Required fields
nl4 = "Block users from filing claims unless a description and priority are provided"

# Example 5: Scope-based
nl5 = "Allow users with scope admin:write to update user profiles when the account is verified"
```

**Important:** When using `generate_policy()` or `start_policy_generation`, the `name` parameter must follow these rules:
- Only letters, numbers, and underscores allowed
- Must start with a letter
- No hyphens, dots, or special characters
- Pattern: `^[A-Za-z][A-Za-z0-9_]*$`

## Testing and Debugging Policies

### LOG_ONLY Mode for Testing

```python
# Create gateway in LOG_ONLY mode for testing
test_cognito = gateway_client.create_oauth_authorizer_with_cognito("test-gateway")
test_gateway = gateway_client.create_mcp_gateway(
    name="test-gateway",
    role_arn=None,
    authorizer_config=test_cognito['authorizer_config'],
    enable_semantic_search=False
)

# Add your Lambda target
test_target = gateway_client.create_mcp_gateway_target(
    gateway=test_gateway,
    name="TestTarget",
    target_type="lambda",
    target_payload={"lambdaArn": "arn:aws:lambda:us-west-2:123456789012:function:TestFunction"},
    credentials=None
)

# Attach Policy Engine in LOG_ONLY mode
gateway_client.update_gateway_policy_engine(
    gateway_identifier=test_gateway["gatewayId"],
    policy_engine_arn=policy_engine['policyEngineArn'],
    mode="LOG_ONLY"  # Test without enforcing
)

# All requests will be allowed, but policy decisions are logged
```


### Policy Validation

```python
# Policies are automatically validated on creation
try:
    policy_client.create_policy(
        policy_engine_id=policy_engine['policyEngineId'],
        name='TestPolicy',
        definition={'cedar': {'statement': invalid_cedar}},
        validation_mode='FAIL_ON_ANY_FINDINGS'
    )
except Exception as e:
    print(f"Validation failed: {e}")
    # Fix the policy and try again
```

## Common Pitfalls and Solutions

### Pitfall 1: Invalid Generation Name

**Problem**: Using hyphens or special characters in policy generation names

**Solution**: Use only letters, numbers, and underscores; must start with a letter

```python
# ❌ Wrong: Contains hyphens
policy_client.generate_policy(
    name='refund-policy-v1',  # ValidationException
    ...
)

# ✅ Correct: Uses underscores
policy_client.generate_policy(
    name='refund_policy_v1',
    ...
)
```

### Pitfall 2: Forgetting Default Deny

**Problem**: Expecting actions to be allowed without a permit policy

**Solution**: Always create explicit permit policies for allowed actions

```python
# ❌ Wrong: No permit policy, everything denied
forbid_policy = """
forbid(principal, action, resource)
when { context.input.amount > 1000 };
"""

# ✅ Correct: Explicit permit for valid cases
permit_policy = """
permit(principal, action, resource)
when { context.input.amount <= 1000 };
"""
```

### Pitfall 3: Vague Conditions

**Problem**: Using subjective terms in conditions

**Solution**: Use precise, testable conditions

```python
# ❌ Wrong: Vague term "reasonable"
"Allow transfers when the amount is reasonable"

# ✅ Correct: Specific threshold
"Allow transfers when the amount is less than $10,000"
```

### Pitfall 4: Missing Tag Checks

**Problem**: Accessing tags without checking if they exist

**Solution**: Always use `hasTag()` before `getTag()`

```python
# ❌ Wrong: May fail if tag doesn't exist
when { principal.getTag("role") == "admin" }

# ✅ Correct: Check existence first
when {
  principal.hasTag("role") &&
  principal.getTag("role") == "admin"
}
```

### Pitfall 5: Incorrect Resource Scope

**Problem**: Using type check with specific actions

**Solution**: Use specific Gateway ARN when specifying tools

```python
# ❌ Wrong: Type check with specific action
resource is AgentCore::Gateway,
action == AgentCore::Action::"SpecificTarget___specific_tool"

# ✅ Correct: Specific Gateway ARN with specific action
resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:region:account:gateway/id",
action == AgentCore::Action::"SpecificTarget___specific_tool"
```

## Policy Management Best Practices

### Version Control Your Policies

```python
# Store policies in version control
policy_definitions = {
    'refund_under_500': {
        'version': '1.0.0',
        'cedar': refund_policy,
        'description': 'Allow refunds under $500'
    },
    'emergency_shutdown': {
        'version': '1.0.0',
        'cedar': emergency_policy,
        'description': 'Emergency refund shutdown'
    }
}

# Deploy from version control
for name, config in policy_definitions.items():
    policy_client.create_or_get_policy(
        policy_engine_id=policy_engine['policyEngineId'],
        name=name,
        definition={'cedar': {'statement': config['cedar']}},
        description=f"{config['description']} (v{config['version']})"
    )
```

### Organize Policies by Purpose

```python
# Group policies by functionality
policies = {
    'authentication': [...],   # Identity-based policies
    'authorization': [...],    # Role/permission-based policies
    'business_rules': [...],   # Amount limits, regional restrictions
    'emergency': [...]         # Shutdown and incident response
}
```

### Test Before Deploying

```python
# 1. Create test gateway with LOG_ONLY
# 2. Run test suite
# 3. Review CloudWatch logs
# 4. Switch to ENFORCE mode

def test_policy_suite(gateway_url, test_cases):
    """Run comprehensive policy tests"""
    results = []
    for test in test_cases:
        response = call_gateway_tool(
            gateway_url,
            test['token'],
            test['tool'],
            test['args']
        )
        results.append({
            'test': test['name'],
            'expected': test['expected'],
            'actual': 'ALLOW' if not response.get('isError') else 'DENY',
            'passed': (not response.get('isError')) == (test['expected'] == 'ALLOW')
        })
    return results
```

## Cleanup

```python
# Delete policies
for policy in policy_client.list_policies(policy_engine['policyEngineId']):
    policy_client.delete_policy(
        policy_engine_id=policy_engine['policyEngineId'],
        policy_id=policy['policyId']
    )

# Delete policy engine (must be detached from gateways first)
policy_client.delete_policy_engine(policy_engine['policyEngineId'])
```

## Next Steps

- [Policy Overview](../user-guide/policy/overview.md) - Understand Policy concepts
- [Policy Quickstart](../user-guide/policy/quickstart.md) - Get started quickly
- [Cedar Documentation](https://docs.cedarpolicy.com/) - Learn Cedar language
- [Gateway Integration](gateway-integration.md) - More Gateway examples
