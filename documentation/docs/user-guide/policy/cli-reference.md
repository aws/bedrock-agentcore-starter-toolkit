# Policy CLI Reference

This guide provides detailed CLI commands for managing Policy Engines and Policies using the AgentCore CLI. For a complete end-to-end tutorial, see the [Policy Quickstart](quickstart.md).

## Policy Engine Management

### List Policy Engines

View all policy engines in your account:

```bash
agentcore policy list-policy-engines --region us-west-2
```

### Create a Policy Engine

Create a new policy engine to organize your policies:

```bash
agentcore policy create-policy-engine \
  --name "MyPolicyEngine" \
  --description "Policy engine for my application" \
  --region us-west-2
```

!!! note "Naming Convention"
    Policy engine names must match the pattern `^[A-Za-z][A-Za-z0-9_]*$` (alphanumeric and underscores, no hyphens).

### Get Policy Engine Details

Retrieve detailed information about a specific policy engine:

```bash
agentcore policy get-policy-engine \
  --engine-id "MyPolicyEngine-abc123" \
  --region us-west-2
```

### Update a Policy Engine

Update the description or configuration of an existing policy engine:

```bash
agentcore policy update-policy-engine \
  --engine-id "MyPolicyEngine-abc123" \
  --description "Updated description" \
  --region us-west-2
```

### Delete a Policy Engine

Remove a policy engine when it's no longer needed:

```bash
agentcore policy delete-policy-engine \
  --engine-id "MyPolicyEngine-abc123" \
  --region us-west-2
```

## Policy Management

### Create a Policy

Define a Cedar policy for your policy engine:

```bash
agentcore policy create-policy \
  --engine-id "MyPolicyEngine-abc123" \
  --name "refund_limit_policy" \
  --description "Allow refunds under $1000" \
  --definition '{
    "cedar": {
      "statement": "permit(principal, action == AgentCore::Action::\"RefundTarget___process_refund\", resource == AgentCore::Gateway::\"arn:aws:bedrock-agentcore:us-west-2:123456789:gateway/my-gateway\") when { context.input.amount < 1000 };"
    }
  }' \
  --region us-west-2
```

### List Policies

View all policies in a policy engine:

```bash
agentcore policy list-policies \
  --engine-id "MyPolicyEngine-abc123" \
  --region us-west-2
```

### Get Policy Details

Retrieve detailed information about a specific policy:

```bash
agentcore policy get-policy \
  --engine-id "MyPolicyEngine-abc123" \
  --policy-id "refund_limit_policy-xyz789" \
  --region us-west-2
```

### Update a Policy

Modify an existing policy:

```bash
agentcore policy update-policy \
  --engine-id "MyPolicyEngine-abc123" \
  --policy-id "refund_limit_policy-xyz789" \
  --description "Updated: Allow refunds under $1500" \
  --definition '{
    "cedar": {
      "statement": "permit(principal, action == AgentCore::Action::\"RefundTarget___process_refund\", resource == AgentCore::Gateway::\"arn:aws:bedrock-agentcore:us-west-2:123456789:gateway/my-gateway\") when { context.input.amount < 1500 };"
    }
  }' \
  --region us-west-2
```

### Delete a Policy

Remove a policy from a policy engine:

```bash
agentcore policy delete-policy \
  --engine-id "MyPolicyEngine-abc123" \
  --policy-id "refund_limit_policy-xyz789" \
  --region us-west-2
```

## Policy Generation

Policy generation allows you to convert natural language descriptions into Cedar policies automatically.

### Start Policy Generation

Generate a Cedar policy from natural language:

```bash
agentcore policy start-policy-generation \
  --engine-id "MyPolicyEngine-abc123" \
  --name "customer_refund_policy" \
  --resource-arn "arn:aws:bedrock-agentcore:us-west-2:123456789:gateway/my-gateway" \
  --content "Allow refunds under 500 dollars for standard customers" \
  --region us-west-2
```

### List Policy Generations

View all policy generation requests:

```bash
agentcore policy list-policy-generations \
  --engine-id "MyPolicyEngine-abc123" \
  --region us-west-2
```

### Get Generation Details

Check the status of a policy generation:

```bash
agentcore policy get-policy-generation \
  --engine-id "MyPolicyEngine-abc123" \
  --generation-id "customer_refund_policy-def456" \
  --region us-west-2
```

The generation will progress through these statuses:

- `GENERATING`: Policy generation in progress
- `GENERATED`: Policy successfully generated
- `FAILED`: Generation failed (check error details)

### List Generation Assets

Retrieve the generated Cedar policy and related assets:

```bash
agentcore policy list-policy-generation-assets \
  --engine-id "MyPolicyEngine-abc123" \
  --generation-id "customer_refund_policy-def456" \
  --region us-west-2
```

## Common Patterns

### Workflow: Create and Test a Policy

1. **Create a policy engine**:
   ```bash
   agentcore policy create-policy-engine \
     --name "TestEngine" \
     --description "Testing policy enforcement" \
     --region us-west-2
   ```

2. **Generate a policy from natural language**:
   ```bash
   agentcore policy start-policy-generation \
     --engine-id "TestEngine-abc123" \
     --name "test_policy" \
     --resource-arn "arn:aws:bedrock-agentcore:us-west-2:123456789:gateway/test-gateway" \
     --content "Allow users to process refunds under $100" \
     --region us-west-2
   ```

3. **Monitor generation status**:
   ```bash
   agentcore policy get-policy-generation \
     --engine-id "TestEngine-abc123" \
     --generation-id "test_policy-xyz" \
     --region us-west-2
   ```

4. **Review generated policy**:
   ```bash
   agentcore policy list-policy-generation-assets \
     --engine-id "TestEngine-abc123" \
     --generation-id "test_policy-xyz" \
     --region us-west-2
   ```

5. **Create the policy** (using the generated Cedar statement):
   ```bash
   agentcore policy create-policy \
     --engine-id "TestEngine-abc123" \
     --name "refund_policy" \
     --description "Allow refunds under $100" \
     --definition '<generated Cedar statement>' \
     --region us-west-2
   ```

## Related Resources

- [Policy Quickstart](quickstart.md) - Complete end-to-end tutorial
- [Policy Overview](overview.md) - Understand Policy Engine concepts
- [Gateway Integration](../gateway/quickstart.md) - Connect policies to your Gateway
