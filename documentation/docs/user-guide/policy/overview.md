# Policy Overview

## Introduction

Policy in Amazon Bedrock AgentCore enables developers to define and enforce security controls for AI agent interactions with tools by creating a protective boundary around agent operations. AI agents can dynamically adapt to solve complex problems - from processing customer inquiries to automating workflows across multiple tools and systems. However, this flexibility introduces new security challenges, as agents may inadvertently misinterpret business rules or act outside their intended authority.

With Policy in Amazon Bedrock AgentCore, you can:

- Create policy engines to store authorization rules
- Write policies using Cedar language (AWS's open-source authorization language)
- Associate policy engines with AgentCore Gateways
- Automatically intercept and evaluate all agent tool calls
- Enforce fine-grained access controls based on user identity and tool parameters

AgentCore Policy intercepts all agent traffic through AgentCore Gateways and evaluates each request against defined policies in the policy engine before allowing tool access.

## Key Benefits

### Fine-grained Control Over Agent Actions

Define what actions an agent is allowed to perform - including which tools it can call and the precise conditions under which those actions are permitted. Control access based on:

- User identity and roles
- OAuth scopes and claims
- Tool input parameters (amounts, regions, types)
- Complex combinations of conditions

### Deterministic Enforcement with Strong Guarantees

Every agent action through AgentCore Gateway is intercepted and evaluated at the boundary outside of the agent's code - ensuring consistent, deterministic enforcement that remains reliable regardless of how the agent is implemented.

### Simple, Accessible Authoring with Organization-wide Consistency

Write policies using natural language prompts or directly in Cedar, making it easy for builders with varying degrees of expertise to define rules for their agents. Teams can set boundaries once and have them applied consistently across all agents and tools, with every enforcement decision logged through CloudWatch metrics and logs for audit and validation.

## Key Features

- **Policy Enforcement** - Intercepts and evaluates all agent requests against defined policies before allowing tool access
- **Access Controls** - Enables fine-grained permissions based on user identity and tool input parameters
- **Policy Authoring** - Provides Cedar policy language support for writing clear, validated policies. Policies can also be authored in natural language using English prompts which are translated into Cedar policies and validated
- **Policy Monitoring** - Offers CloudWatch integration for monitoring policy evaluations and decisions
- **Infrastructure Integration** - Integrates with VPC security groups and other AWS security infrastructure
- **Audit Logging** - Maintains detailed logs of policy decisions for compliance and troubleshooting

## Core Concepts

### Gateway

An AgentCore Gateway provides an endpoint to connect to MCP servers and convert APIs and Lambda functions to MCP-compatible tools, providing a single access point for an agent to interact with its tools. A Gateway can have multiple targets, each representing a different tool or set of tools.

### Policy Engine

The policy engine is the component of Policy in AgentCore that stores and evaluates Cedar policies. When you create policies, they apply to every gateway associated with the engine, as long as the policy scope matches the request. For every tool invocation, the policy engine evaluates all applicable policies against the request to determine whether to allow or deny access.

### Cedar

[Cedar](https://docs.cedarpolicy.com/) is an open-source policy language developed by AWS for writing and enforcing authorization policies. Cedar policies are:

- **Human-readable** - Clear syntax that developers can understand
- **Analyzable** - Automated reasoning can detect policy issues
- **Validated** - Policies are checked against schemas at creation time

Policy in AgentCore uses Cedar to provide precise, verifiable access control for gateway tools.

### Cedar Policy Structure

A Cedar policy is a declarative statement that permits or forbids access to gateway tools. Each policy specifies:

- **Who** (principal) - The user or entity making the request
- **What** (action) - The operation being requested (tool invocation)
- **Which** (resource) - The target gateway
- **When** (conditions) - Additional logic that must be satisfied

Example policy:
```cedar
permit(
  principal is AgentCore::OAuthUser,
  action == AgentCore::Action::"RefundTool__process_refund",
  resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/refund-gateway"
)
when {
  principal.hasTag("username") &&
  principal.getTag("username") == "refund-agent" &&
  context.input.amount < 500
};
```

This policy allows the user "refund-agent" to process refunds only when the amount is less than $500.

### Authorization Semantics

Cedar uses a **forbid-overrides-permit** evaluation model:

1. **Default Deny** - All actions are denied by default. If no policies match a request, Cedar returns DENY
2. **Forbid Wins** - If any forbid policy matches, the result is DENY, even if permit policies also match
3. **At Least One Permit Required** - If at least one permit policy matches and no forbid policies do, the result is ALLOW

### Policy Enforcement Modes

Policy engines support two enforcement modes:

- **LOG_ONLY** - Evaluates and logs policy decisions without enforcing them (useful for testing)
- **ENFORCE** - Evaluates and enforces decisions by allowing or denying agent operations

### Natural Language Policy Authoring

Policy in Amazon Bedrock AgentCore provides the capability to author policies using natural language by allowing developers to describe rules in plain English instead of writing formal policy code in Cedar. The service:

- Interprets what the user intends
- Generates candidate Cedar policies
- Validates them against the tool schema
- Uses automated reasoning to check safety conditions
- Identifies overly permissive, overly restrictive, or invalid policies

This ensures you catch issues before enforcing policies.

## Authorization Flow

Understanding how authorization information flows through the system:

### 1. Request Processing

AgentCore Gateway processes two key pieces of information:

**JWT Token** - OAuth claims about the user:
```json
{
  "sub": "user-123",
  "username": "refund-agent",
  "scope": "refund:write admin:read",
  "role": "admin"
}
```

**MCP Tool Call** - The actual tool invocation:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "RefundTool__process_refund",
    "arguments": {
      "orderId": "12345",
      "amount": 450
    }
  }
}
```

### 2. Cedar Authorization Request

The Gateway constructs a Cedar authorization request:

- **Principal**: `AgentCore::OAuthUser::"user-123"` (from JWT sub claim)
- **Action**: `AgentCore::Action::"RefundTool__process_refund"` (from tool name)
- **Resource**: `AgentCore::Gateway::"arn:aws:..."` (the Gateway instance)
- **Context**: `{"input": {"orderId": "12345", "amount": 450}}` (tool arguments)
- **Tags**: JWT claims stored as tags on the OAuthUser entity

### 3. Policy Evaluation

Cedar evaluates all policies against the request:

- ✓ Principal check: Is the principal an OAuthUser?
- ✓ Action check: Is the action RefundTool__process_refund?
- ✓ Resource check: Is the resource the refund gateway?
- ✓ Condition checks: Does username = "refund-agent"? Is amount < 500?

Result: **ALLOW** or **DENY**

## Limitations

### Cedar Language Limitations

- No floating-point numbers (use Decimal for fractional values, limited to 4 decimal places)
- No regular expressions (pattern matching limited to `like` operator with `*` wildcards)

### Current Implementation Limitations

- No date/time support for date and time comparisons
- Custom claims in natural language policy authoring must be provided in the prompt
- Limited decimal precision (4 decimal places)
- Cedar schema size limited to 200 KB
- Maximum 1000 policies per engine
- Maximum 1000 policy engines per account

## Next Steps

- [Policy Quickstart](quickstart.md) - Get started with your first policy
- [Policy Integration Examples](../../examples/policy-integration.md) - See real-world policy patterns
- [Cedar Documentation](https://docs.cedarpolicy.com/) - Learn more about the Cedar language

## Additional Resources

- [AWS Developer Guide - Policy in AgentCore](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/policy.html)
- [Cedar Policy Language](https://www.cedarpolicy.com/)
- [Gateway Integration Guide](../gateway/quickstart.md)
