# CLI

Command-line interface for BedrockAgentCore Starter Toolkit.

The `agentcore` CLI provides commands for configuring, launching, managing agents, and working with gateways.

## Runtime Commands

### Configure

Configure agents and runtime environments.

```
agentcore configure [OPTIONS]
```

Options:

- `--entrypoint, -e TEXT`: Python file of agent
- `--name, -n TEXT`: Agent name (defaults to Python file name)
- `--execution-role, -er TEXT`: IAM execution role ARN
- `--code-build-execution-role, -cber TEXT`: CodeBuild execution role ARN (uses execution-role if not provided)
- `--ecr, -ecr TEXT`: ECR repository name (use “auto” for automatic creation)
- `--container-runtime, -ctr TEXT`: Container runtime (for container deployment only)
- `--deployment-type, -dt TEXT`: Deployment type (direct_code_deploy or container, default: direct_code_deploy)
- `--runtime, -rt TEXT`: Python runtime version for direct_code_deploy (PYTHON_3_10, PYTHON_3_11, PYTHON_3_12, PYTHON_3_13)
- `--requirements-file, -rf TEXT`: Path to requirements file of agent
- `--disable-otel, -do`: Disable OpenTelemetry
- `--disable-memory, -dm`: Disable memory (skip memory setup entirely)
- `--authorizer-config, -ac TEXT`: OAuth authorizer configuration as JSON string
- `--request-header-allowlist, -rha TEXT`: Comma-separated list of allowed request headers
- `--vpc`: Enable VPC networking mode (requires --subnets and --security-groups)
- `--subnets TEXT`: Comma-separated list of subnet IDs (required with --vpc)
- `--security-groups TEXT`: Comma-separated list of security group IDs (required with --vpc)
- `--idle-timeout, -it INTEGER`: Seconds before idle session terminates (60-28800, default: 900)
- `--max-lifetime, -ml INTEGER`: Maximum instance lifetime in seconds (60-28800, default: 28800)
- `--verbose, -v`: Enable verbose output
- `--region, -r TEXT`: AWS region
- `--protocol, -p TEXT`: Agent server protocol (HTTP or MCP or A2A)
- `--non-interactive, -ni`: Skip prompts; use defaults unless overridden
- `--vpc`: Enable VPC networking mode for secure access to private resources
- `--subnets TEXT`: Comma-separated list of subnet IDs (required when --vpc is enabled)
- `--security-groups TEXT`: Comma-separated list of security group IDs (required when --vpc is enabled)

Subcommands:

- `list`: List configured agents
- `set-default`: Set default agent

**Memory Configuration:**

Memory is **opt-in** by default. To enable memory:

```
# Interactive mode - prompts for memory setup
agentcore configure --entrypoint agent.py
# Options during prompt:
#   - Use existing memory (select by number)
#   - Create new memory (press Enter, then choose STM only or STM+LTM)
#   - Skip memory setup (type 's')

# Explicitly disable memory
agentcore configure --entrypoint agent.py --disable-memory

# Non-interactive mode (uses STM only by default)
agentcore configure --entrypoint agent.py --non-interactive
```

**Memory Modes:**

- **NO_MEMORY** (default): No memory resources created
- **STM_ONLY**: Short-term memory (30-day retention, stores conversations within sessions)
- **STM_AND_LTM**: Short-term + Long-term memory (extracts preferences, facts, and summaries across sessions)

**Region Configuration:**

```
# Use specific region
agentcore configure -e agent.py --region us-east-1

# Region precedence:
# 1. --region flag
# 2. AWS_DEFAULT_REGION environment variable
# 3. AWS CLI configured region
```

**VPC Networking:**

When enabled, agents run within your VPC for secure access to private resources:

- **Requirements:**
- All subnets must be in the same VPC
- Subnets must be in supported Availability Zones
- Security groups must allow required egress traffic
- Automatically creates `AWSServiceRoleForBedrockAgentCoreNetwork` service-linked role if needed
- **Validation:**
- Validates subnets belong to the same VPC
- Checks subnet availability zones are supported
- Verifies security groups exist and are properly configured
- **Network Immutability:**
- VPC configuration cannot be changed after initial deployment
- To modify network settings, create a new agent configuration

**Lifecycle Configuration:**

Session lifecycle management controls when runtime sessions automatically terminate:

- **Idle Timeout**: Terminates session after specified seconds of inactivity (60-28800 seconds)
- **Max Lifetime**: Terminates session after maximum runtime regardless of activity (60-28800 seconds)
- Validation ensures `max-lifetime >= idle-timeout`

```
# Configure with lifecycle settings
agentcore configure --entrypoint agent.py \
  --idle-timeout 1800 \    # 30 minutes idle before termination
  --max-lifetime 7200      # 2 hours max regardless of activity
```

### Deploy

Deploy agents to AWS or run locally.

```
agentcore deploy [OPTIONS]
```

Options:

- `--agent, -a TEXT`: Agent name
- `--local, -l`: Build and run locally (requires Docker/Finch/Podman)
- `--local-build, -lb`: Build locally and deploy to cloud (requires Docker/Finch/Podman)
- `--auto-update-on-conflict, -auc`: Automatically update existing agent instead of failing
- `--env, -env TEXT`: Environment variables for agent (format: KEY=VALUE)

**Deployment Modes:**

```
# CodeBuild (default) - Cloud build, no Docker required
agentcore deploy

# Local mode - Build and run locally
agentcore deploy --local

# Local build mode - Build locally, deploy to cloud
agentcore deploy --local-build
```

**Memory Provisioning:**

During deploy, if memory is enabled:

- Memory resources are created and provisioned
- Deploy waits for memory to become ACTIVE before proceeding
- STM provisioning: ~30-90 seconds
- LTM provisioning: ~120-180 seconds
- Progress updates displayed during wait

### Invoke

Invoke deployed agents.

```
agentcore invoke [PAYLOAD] [OPTIONS]
```

Arguments:

- `PAYLOAD`: JSON payload to send

Options:

- `--agent, -a TEXT`: Agent name
- `--session-id, -s TEXT`: Session ID
- `--bearer-token, -bt TEXT`: Bearer token for OAuth authentication
- `--local, -l`: Send request to a running local agent (works with both direct_code_deploy and container deployments)
- `--user-id, -u TEXT`: User ID for authorization flows
- `--headers TEXT`: Custom headers (format: ‘Header1:value,Header2:value2’)

**Custom Headers:**

Headers will be auto-prefixed with `X-Amzn-Bedrock-AgentCore-Runtime-Custom-` if not already present:

```
# These are equivalent:
agentcore invoke '{"prompt": "test"}' --headers "Actor-Id:user123"
agentcore invoke '{"prompt": "test"}' --headers "X-Amzn-Bedrock-AgentCore-Runtime-Custom-Actor-Id:user123"
```

**Example Output:**

- Session and Request IDs displayed in panel header
- CloudWatch log commands ready to copy
- GenAI Observability Dashboard link (when OTEL enabled)
- Proper UTF-8 character rendering
- Clean response formatting without raw data structures

Example output:

```
╭────────── agent_name ──────────╮
│ Session: abc-123                │
│ Request ID: req-456             │
│ ARN: arn:aws:bedrock...         │
│ Logs: aws logs tail ... --follow│
│ GenAI Dashboard: https://...    │
╰─────────────────────────────────╯

Response:
Your formatted response here
```

### Status

Get Bedrock AgentCore status including config and runtime details, and VPC configuration.

```
agentcore status [OPTIONS]
```

Options:

- `--agent, -a TEXT`: Agent name
- `--verbose, -v`: Verbose JSON output of config, agent, and endpoint status

**Status Display:**

Shows comprehensive agent information including:

- Agent deployment status
- Memory configuration and status (Disabled/CREATING/ACTIVE)
- Endpoint readiness
- VPC networking configuration (when enabled):
- VPC ID
- Subnet IDs and Availability Zones
- Security Group IDs
- Network mode indicator
- CloudWatch log paths
- GenAI Observability Dashboard link (when OTEL enabled)

### Destroy

Destroy Bedrock AgentCore resources.

```
agentcore destroy [OPTIONS]
```

Options:

- `--agent, -a TEXT`: Agent name
- `--dry-run`: Show what would be destroyed without actually destroying
- `--force`: Skip confirmation prompts
- `--delete-ecr-repo`: Also delete the ECR repository after removing images

**Destroyed Resources:**

- AgentCore endpoint
- AgentCore agent runtime
- ECR images
- CodeBuild project
- IAM execution role (if not used by other agents)
- Memory resources (if created by toolkit)
- Agent deployment configuration

```
# Preview what would be destroyed
agentcore destroy --dry-run

# Destroy with confirmation
agentcore destroy --agent my-agent

# Destroy without confirmation
agentcore destroy --agent my-agent --force

# Destroy and delete ECR repository
agentcore destroy --agent my-agent --delete-ecr-repo
```

### Stop Session

Terminate active runtime sessions to free resources and reduce costs.

```
agentcore stop-session [OPTIONS]
```

**Session Tracking:**

The CLI automatically tracks the runtime session ID from the last `agentcore invoke` command. This allows you to stop sessions without manually specifying the session ID.

**Examples:**

```
# Stop the last invoked session (tracked automatically)
agentcore stop-session

# Stop a specific session by ID
agentcore stop-session --session-id abc123xyz

# Stop session for specific agent
agentcore stop-session --agent my-agent --session-id abc123xyz
```

Options:

- `--session-id, -s TEXT`: Specific session ID to stop (optional)
- `--agent, -a TEXT`: Agent name

## Identity Commands

Manage AgentCore Identity resources for OAuth authentication and external service access.

### Setup Cognito

Create Cognito user pools for Identity authentication.

```
agentcore identity setup-cognito [OPTIONS]
```

Options:

- `--region, -r TEXT`: AWS region (defaults to configured region)
- `--auth-flow TEXT`: OAuth flow type - ‘user’ (USER_FEDERATION) or ‘m2m’ (M2M). Default: ‘user’

**Auth Flow Types:**

- `user` (default): USER_FEDERATION flow requiring user login and consent
- Creates user pool with hosted UI
- Generates test user credentials
- For agents that act on behalf of users
- `m2m`: M2M flow for machine-to-machine
- Creates user pool with resource server and scopes
- No user accounts needed
- For agents that authenticate as themselves

**What it creates:**

**1. Cognito Agent User Pool**: Manages user authentication to your agent

- **Purpose**: Authenticates users TO your agent
- **Flow**: User → Cognito → JWT → Agent Runtime
- **Contains**: User directory for agent access
- **Environment prefix**: `RUNTIME_*`

**2. Cognito Resource User Pool**: Enables agent to access external resources

- **Purpose**: Agent authenticates TO external services (GitHub, Google, etc.)
- **Flow**: Agent → Identity → External Service
- **Contains**: OAuth client credentials
- **Environment prefix**: `IDENTITY_*`

**Output:**

- Displays Runtime and Identity pool configurations (passwords hidden)
- Saves to `.agentcore_identity_cognito_{flow}.json` (flow-specific JSON)
- Saves to `.agentcore_identity_{flow}.env` (flow-specific environment variables)
- Provides copy-paste commands using actual values

**Security:**

- .env files have owner-only permissions (chmod 600)
- Passwords and secrets not echoed to terminal
- Flow-specific files prevent conflicts when using both flows

**Examples:**

```
# Create pools for user consent flow (default)
agentcore identity setup-cognito

# Create pools for machine-to-machine flow
agentcore identity setup-cognito --auth-flow m2m

# Load environment variables (bash/zsh)
export $(grep -v '^#' .agentcore_identity_user.env | xargs)
# or for m2m:
export $(grep -v '^#' .agentcore_identity_m2m.env | xargs)

# In Python
from dotenv import load_dotenv
load_dotenv('.agentcore_identity_user.env')
```

### Create Credential Provider

Create an OAuth 2.0 credential provider for external service authentication.

```
agentcore identity create-credential-provider [OPTIONS]
```

Options:

- `--name TEXT`: Provider name (required)
- `--type TEXT`: Provider type: cognito, github, google, salesforce (required)
- `--client-id TEXT`: OAuth 2.0 client ID (required)
- `--client-secret TEXT`: OAuth 2.0 client secret (required)
- `--discovery-url TEXT`: OIDC discovery URL (required for cognito)
- `--cognito-pool-id TEXT`: Cognito User Pool ID (optional, for auto-updating callback URLs)
- `--region TEXT`: AWS region (defaults to configured region)

**Provider Types:**

- `cognito`: Amazon Cognito User Pools
- `github`: GitHub OAuth
- `google`: Google OAuth
- `salesforce`: Salesforce OAuth

**Discovery URL Format:** Must be the complete OIDC discovery URL including `.well-known/openid-configuration`:

```
# Cognito format
https://cognito-idp.us-west-2.amazonaws.com/us-west-2_xxxxx/.well-known/openid-configuration
```

**Automatic Configuration:**

- Creates the credential provider in AgentCore Identity
- Adds provider configuration to `.bedrock_agentcore.yaml`
- IAM permissions added automatically during `agentcore deploy`

**Note:** After creating a provider, you must register the returned `callbackUrl` in your OAuth provider’s settings (except for Cognito, which is auto-configured with `--cognito-pool-id`).

**Examples:**

```
# Using environment variables from setup-cognito
agentcore identity create-credential-provider \
  --name MyServiceProvider \
  --type cognito \
  --client-id $IDENTITY_CLIENT_ID \
  --client-secret $IDENTITY_CLIENT_SECRET \
  --discovery-url $IDENTITY_DISCOVERY_URL \
  --cognito-pool-id $IDENTITY_POOL_ID

# GitHub provider
agentcore identity create-credential-provider \
  --name MyGitHub \
  --type github \
  --client-id "github_client_id" \
  --client-secret "github_client_secret"

# IMPORTANT: Register the callback URL from the response
# in your GitHub OAuth app settings
```

### Create Workload Identity

Create a workload identity for agent-to-Identity service authentication.

```
agentcore identity create-workload-identity [OPTIONS]
```

Options:

- `--name TEXT`: Workload identity name (auto-generated if not provided)
- `--region TEXT`: AWS region (defaults to configured region)

**Example:**

```
agentcore identity create-workload-identity --name my-workload
```

### Get Cognito Inbound Token

Generate a JWT bearer token from Cognito for Runtime inbound authentication.

Automatically loads credentials from environment variables. Explicit parameters override environment variables.

```
agentcore identity get-cognito-inbound-token [OPTIONS]
```

Options:

- `--auth-flow TEXT`: OAuth flow type - ‘user’ (USER_FEDERATION, default) or ‘m2m’ (M2M)
- `--pool-id TEXT`: Cognito User Pool ID (auto-loads from RUNTIME_POOL_ID)
- `--client-id TEXT`: Cognito App Client ID (auto-loads from RUNTIME_CLIENT_ID)
- `--client-secret TEXT`: Client secret (auto-loads from RUNTIME_CLIENT_SECRET, required for m2m)
- `--username TEXT`: Username (auto-loads from RUNTIME_USERNAME, required for user flow)
- `--password TEXT`: Password (auto-loads from RUNTIME_PASSWORD, required for user flow)
- `--region TEXT`: AWS region

**Examples:**

```
# Auto-load from environment (user flow - simplest)
export $(grep -v '^#' .agentcore_identity_user.env | xargs)
TOKEN=$(agentcore identity get-cognito-inbound-token)

# Auto-load from environment (m2m flow)
export $(grep -v '^#' .agentcore_identity_m2m.env | xargs)
TOKEN=$(agentcore identity get-cognito-inbound-token --auth-flow m2m)

# Explicit parameters (overrides env)
TOKEN=$(agentcore identity get-cognito-inbound-token \
         --pool-id us-west-2_xxx --client-id abc123 \
         --username user --password pass)

# Use token with agent
agentcore invoke '{"prompt": "test"}' --bearer-token "$TOKEN"
```

### Cleanup Identity Resources

Remove all Identity resources for an agent.

```
agentcore identity cleanup [OPTIONS]
```

Options:

- `--agent, -a TEXT`: Agent name
- `--force, -f`: Skip confirmation prompts

**Deleted Resources:**

- Credential providers
- Workload identities
- Cognito user pools (if created by setup-cognito)
- IAM inline policies (AgentCoreIdentityAccess)
- Configuration files (.agentcore_identity\_\*)

**Example:**

```
# Clean up with confirmation
agentcore identity cleanup --agent my-agent

# Clean up without prompts
agentcore identity cleanup --agent my-agent --force
```

## Identity Example Usage

### Complete Identity Setup Workflow

```
# 1. Create Cognito pools
agentcore identity setup-cognito

# 2. Load environment variables
export $(grep -v '^#' .agentcore_identity_user.env | xargs)

# 3. Configure agent with JWT auth
agentcore configure \
  -e agent.py \
  --name my-agent \
  --authorizer-config '{
    "customJWTAuthorizer": {
      "discoveryUrl": "'$RUNTIME_DISCOVERY_URL'",
      "allowedClients": ["'$RUNTIME_CLIENT_ID'"]
    }
  }' \
  --disable-memory

# 4. Create credential provider
agentcore identity create-credential-provider \
  --name MyServiceProvider \
  --type cognito \
  --client-id $IDENTITY_CLIENT_ID \
  --client-secret $IDENTITY_CLIENT_SECRET \
  --discovery-url $IDENTITY_DISCOVERY_URL \
  --cognito-pool-id $IDENTITY_POOL_ID

# 5. Create workload identity
agentcore identity create-workload-identity \
  --name my-agent-workload

# 6. Deploy agent
agentcore deploy

# 7. Get bearer token for Runtime auth
TOKEN=$(agentcore identity get-cognito-inbound-token)

# 8. Invoke with JWT authentication
agentcore invoke '{"prompt": "Call external service"}' \
  --bearer-token "$TOKEN" \
  --session-id "demo_session_$(uuidgen | tr -d '-')"

# 9. Cleanup when done
agentcore identity cleanup --agent my-agent --force
```

## Memory Commands

Manage AgentCore Memory resources:

```
agentcore memory [COMMAND]
```

### Create Memory

```
agentcore memory create NAME [OPTIONS]
```

Arguments:

- `NAME`: Name for the memory resource (required)

Options:

- `--region, -r TEXT`: AWS region (defaults to session region)
- `--description, -d TEXT`: Description for the memory
- `--event-expiry-days, -e INTEGER`: Event retention in days (defaults to 90)
- `--strategies, -s TEXT`: JSON string of memory strategies (e.g., '[{"semanticMemoryStrategy": {"name": "Facts"}}]')
- `--role-arn TEXT`: IAM role ARN for memory execution
- `--encryption-key-arn TEXT`: KMS key ARN for encryption
- `--wait/--no-wait`: Wait for memory to become ACTIVE (defaults to True)
- `--max-wait INTEGER`: Maximum wait time in seconds (defaults to 300)

**Examples:**

```
# Create basic memory (STM only)
agentcore memory create my_agent_memory

# Create with LTM strategies
agentcore memory create my_memory --strategies '[{"semanticMemoryStrategy": {"name": "Facts"}}]' --wait
```

### Get Memory

```
agentcore memory get MEMORY_ID [OPTIONS]
```

Arguments:

- `MEMORY_ID`: Memory resource ID (required)

Options:

- `--region, -r TEXT`: AWS region

**Example:**

```
agentcore memory get my_memory_abc123
```

### List Memories

```
agentcore memory list [OPTIONS]
```

Options:

- `--region, -r TEXT`: AWS region
- `--max-results, -n INTEGER`: Maximum number of results (defaults to 100)

**Example:**

```
agentcore memory list
```

### Delete Memory

```
agentcore memory delete MEMORY_ID [OPTIONS]
```

Arguments:

- `MEMORY_ID`: Memory resource ID to delete (required)

Options:

- `--region, -r TEXT`: AWS region
- `--wait`: Wait for deletion to complete
- `--max-wait INTEGER`: Maximum wait time in seconds (defaults to 300)

**Example:**

```
agentcore memory delete my_memory_abc123 --wait
```

### Memory Status

```
agentcore memory status MEMORY_ID [OPTIONS]
```

Arguments:

- `MEMORY_ID`: Memory resource ID (required)

Options:

- `--region, -r TEXT`: AWS region

**Example:**

```
agentcore memory status mem_123
```

## Gateway Commands

Access gateway subcommands:

```
agentcore gateway [COMMAND]
```

### Create MCP Gateway

```
agentcore gateway create-mcp-gateway [OPTIONS]
```

Options:

- `--region TEXT`: Region to use (defaults to us-west-2)
- `--name TEXT`: Name of the gateway (defaults to TestGateway)
- `--role-arn TEXT`: Role ARN to use (creates one if none provided)
- `--authorizer-config TEXT`: Serialized authorizer config
- `--enable-semantic-search, -sem`: Whether to enable search tool (defaults to True)

### Create MCP Gateway Target

```
agentcore gateway create-mcp-gateway-target [OPTIONS]
```

Options:

- `--gateway-arn TEXT`: ARN of the created gateway (required)
- `--gateway-url TEXT`: URL of the created gateway (required)
- `--role-arn TEXT`: Role ARN of the created gateway (required)
- `--region TEXT`: Region to use (defaults to us-west-2)
- `--name TEXT`: Name of the target (defaults to TestGatewayTarget)
- `--target-type TEXT`: Type of target: lambda, openApiSchema, mcpServer, or smithyModel (defaults to lambda)
- `--target-payload TEXT`: Specification of the target (required for openApiSchema)
- `--credentials TEXT`: Credentials for calling this target (API key or OAuth2)

### Delete MCP Gateway

```
agentcore gateway delete-mcp-gateway [OPTIONS]
```

Options:

- `--region TEXT`: Region to use (defaults to us-west-2)
- `--id TEXT`: Gateway ID to delete
- `--name TEXT`: Gateway name to delete
- `--arn TEXT`: Gateway ARN to delete
- `--force`: Delete all targets before deleting the gateway

**Note:** The gateway must have zero targets before deletion, unless `--force` is used. You can specify the gateway by ID, ARN, or name.

### Delete MCP Gateway Target

```
agentcore gateway delete-mcp-gateway-target [OPTIONS]
```

Options:

- `--region TEXT`: Region to use (defaults to us-west-2)
- `--id TEXT`: Gateway ID
- `--name TEXT`: Gateway name
- `--arn TEXT`: Gateway ARN
- `--target-id TEXT`: Target ID to delete
- `--target-name TEXT`: Target name to delete

**Note:** You can specify the gateway by ID, ARN, or name. You can specify the target by ID or name.

### List MCP Gateways

```
agentcore gateway list-mcp-gateways [OPTIONS]
```

Options:

- `--region TEXT`: Region to use
- `--name TEXT`: Filter by gateway name
- `--max-results, -m INTEGER`: Maximum number of results (1-1000, defaults to 50)

### Get MCP Gateway

```
agentcore gateway get-mcp-gateway [OPTIONS]
```

Options:

- `--region TEXT`: Region to use
- `--id TEXT`: Gateway ID
- `--name TEXT`: Gateway name
- `--arn TEXT`: Gateway ARN

**Note:** You can specify the gateway by ID, ARN, or name.

### List MCP Gateway Targets

```
agentcore gateway list-mcp-gateway-targets [OPTIONS]
```

Options:

- `--region TEXT`: Region to use
- `--id TEXT`: Gateway ID
- `--name TEXT`: Gateway name
- `--arn TEXT`: Gateway ARN
- `--max-results, -m INTEGER`: Maximum number of results (1-1000, defaults to 50)

**Note:** You can specify the gateway by ID, ARN, or name.

### Get MCP Gateway Target

```
agentcore gateway get-mcp-gateway-target [OPTIONS]
```

Options:

- `--region TEXT`: Region to use
- `--id TEXT`: Gateway ID
- `--name TEXT`: Gateway name
- `--arn TEXT`: Gateway ARN
- `--target-id TEXT`: Target ID
- `--target-name TEXT`: Target name

**Note:** You can specify the gateway by ID, ARN, or name. You can specify the target by ID or name.

### Update Gateway

Update gateway configuration including description and policy engine.

**Note:** Gateway names cannot be updated after creation (AWS API limitation).

```
agentcore gateway update-gateway [OPTIONS]
```

Options:

- `--region TEXT`: AWS region to use (defaults to us-west-2)
- `--id TEXT`: Gateway ID to update
- `--arn TEXT`: Gateway ARN to update
- `--description TEXT`: New gateway description
- `--policy-engine-arn TEXT`: Policy engine ARN to attach
- `--policy-engine-mode TEXT`: Policy engine mode (LOG_ONLY or ENFORCE)

**Note:** You can specify the gateway by ID or ARN. To attach or update a policy engine, use the `--policy-engine-arn` and `--policy-engine-mode` options with the `update-gateway` command.

## Policy Commands

Manage AgentCore Policy resources for governance and authorization.

Access policy subcommands:

```
agentcore policy [COMMAND]
```

### Create Policy Engine

Create a new policy engine to manage Cedar policies.

```
agentcore policy create-policy-engine [OPTIONS]
```

Options:

- `--name, -n TEXT`: Name of the policy engine (required)
- `--region, -r TEXT`: AWS region (defaults to us-east-1)
- `--description, -d TEXT`: Policy engine description (optional)

**Example:**

```
agentcore policy create-policy-engine \
  --name "RefundPolicyEngine" \
  --description "Policy engine to regulate refund operations"
```

### Get Policy Engine

Get details of a policy engine.

```
agentcore policy get-policy-engine [OPTIONS]
```

Options:

- `--policy-engine-id, -e TEXT`: Policy engine ID (required)
- `--region, -r TEXT`: AWS region (defaults to us-east-1)

**Example:**

```
agentcore policy get-policy-engine --policy-engine-id "testPolicyEngine-abc123"
```

### Update Policy Engine

Update a policy engine's properties.

```
agentcore policy update-policy-engine [OPTIONS]
```

Options:

- `--policy-engine-id, -e TEXT`: Policy engine ID (required)
- `--region, -r TEXT`: AWS region (defaults to us-east-1)
- `--description, -d TEXT`: Updated description (optional)

**Example:**

```
agentcore policy update-policy-engine \
  --policy-engine-id "testPolicyEngine-abc123" \
  --description "Updated policy engine description"
```

### List Policy Engines

List all policy engines in the region.

```
agentcore policy list-policy-engines [OPTIONS]
```

Options:

- `--region, -r TEXT`: AWS region (defaults to us-east-1)
- `--max-results INTEGER`: Maximum number of results (optional)
- `--next-token TEXT`: Token for pagination (optional)

**Example:**

```
agentcore policy list-policy-engines --max-results 50
```

### Delete Policy Engine

Delete a policy engine.

```
agentcore policy delete-policy-engine [OPTIONS]
```

Options:

- `--policy-engine-id, -e TEXT`: Policy engine ID (required)
- `--region, -r TEXT`: AWS region (defaults to us-east-1)

**Example:**

```
agentcore policy delete-policy-engine --policy-engine-id "testPolicyEngine-abc123"
```

### Create Policy

Create a new Cedar policy in a policy engine.

```
agentcore policy create-policy [OPTIONS]
```

Options:

- `--policy-engine-id, -e TEXT`: Policy engine ID (required)
- `--name, -n TEXT`: Policy name (required)
- `--definition, -def TEXT`: Policy definition JSON (required)
- `--region, -r TEXT`: AWS region (defaults to us-east-1)
- `--description, -d TEXT`: Policy description (optional)
- `--validation-mode TEXT`: Validation mode - FAIL_ON_ANY_FINDINGS or IGNORE_ALL_FINDINGS (optional)

**Policy Definition Format:**

The definition must be a JSON string containing Cedar policy statements. Cedar policies require resource constraints and do not support glob-style wildcards:

```
{
  "cedar": {
    "statement": "permit(principal, action == AgentCore::Action::\"RefundTarget___process_refund\", resource == AgentCore::Gateway::\"arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway/my-gateway\") when { context.input.amount < 1000 };"
  }
}
```

**Action Name Format:**

Action names follow the pattern `TargetName___tool_name` (triple underscore):

- Format: `AgentCore::Action::"<TargetName>___<tool_name>"`
- Example: `AgentCore::Action::"RefundTarget___process_refund"`
- The target name and tool name are separated by **three underscores** (`___`)

**Resource Constraints:**

Cedar policies must specify a specific Gateway ARN:

- **Specific Gateway:** `resource == AgentCore::Gateway::"arn:aws:bedrock-agentcore:region:account:gateway/id"`

❌ **Invalid:** `permit(principal, action, resource);` - Unconstrained wildcard resources are not allowed

**Important Note on Numeric Comparisons:**

When using numeric comparisons in Cedar conditions, the JSON Schema type matters:

- **`"type": "integer"`** (maps to Cedar Long) → Use direct comparison operators: `<`, `>`, `<=`, `>=`, `==`

  ```
  context.input.amount < 1000
  ```

- **`"type": "number"`** (maps to Cedar Decimal) → Use comparison methods: `.lessThan()`, `.greaterThan()`, `.lessThanOrEqual()`, `.greaterThanOrEqual()`

  ```
  context.input.amount.lessThan(decimal("1000.00"))
  ```

For simplicity, use `"type": "integer"` for whole number amounts (like dollar amounts) to enable direct comparison operators.

**Tip: Use `.contains()` for Multiple Value Checks:**

Instead of chaining multiple OR conditions, use `.contains()` with a set:

```
// ❌ Verbose
context.input.region == "US" || context.input.region == "CA" || context.input.region == "UK"

// ✅ Cleaner
["US", "CA", "UK"].contains(context.input.region)
```

**Example:**

```
agentcore policy create-policy \
  --policy-engine-id "testPolicyEngine-abc123" \
  --name "refund_limit_policy" \
  --description "Allow refunds under \$1000" \
  --definition '{"cedar":{"statement":"permit(principal, action == AgentCore::Action::\"RefundTarget___process_refund\", resource == AgentCore::Gateway::\"arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway/my-gateway\") when { context.input.amount < 1000 };"}}'
```

### Get Policy

Get details of a specific policy.

```
agentcore policy get-policy [OPTIONS]
```

Options:

- `--policy-engine-id, -e TEXT`: Policy engine ID (required)
- `--policy-id, -p TEXT`: Policy ID (required)
- `--region, -r TEXT`: AWS region (defaults to us-east-1)

**Example:**

```
agentcore policy get-policy \
  --policy-engine-id "testPolicyEngine-abc123" \
  --policy-id "policy-xyz789"
```

### Update Policy

Update an existing policy's definition.

```
agentcore policy update-policy [OPTIONS]
```

Options:

- `--policy-engine-id, -e TEXT`: Policy engine ID (required)
- `--policy-id, -p TEXT`: Policy ID (required)
- `--definition, -def TEXT`: Updated policy definition JSON (required)
- `--region, -r TEXT`: AWS region (defaults to us-east-1)
- `--description, -d TEXT`: Updated description (optional)
- `--validation-mode TEXT`: Validation mode (optional)

**Example:**

```
agentcore policy update-policy \
  --policy-engine-id "testPolicyEngine-abc123" \
  --policy-id "policy-xyz789" \
  --definition '{"cedar":{"statement":"permit(principal, action == AgentCore::Action::\"RefundTarget___process_refund\", resource == AgentCore::Gateway::\"arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway/my-gateway\") when { context.input.amount < 500 };"}}' \
  --description "Updated to \$500 limit"
```

### List Policies

List policies in a policy engine.

```
agentcore policy list-policies [OPTIONS]
```

Options:

- `--policy-engine-id, -e TEXT`: Policy engine ID (required)
- `--region, -r TEXT`: AWS region (defaults to us-east-1)
- `--target-resource-scope TEXT`: Filter by resource ARN (optional)
- `--max-results INTEGER`: Maximum number of results (optional)
- `--next-token TEXT`: Token for pagination (optional)

**Example:**

```
# List all policies
agentcore policy list-policies --policy-engine-id "testPolicyEngine-abc123"

# Filter by resource
agentcore policy list-policies \
  --policy-engine-id "testPolicyEngine-abc123" \
  --target-resource-scope "arn:aws:bedrock-agentcore:us-east-1:123456789012:gateway/my-gateway"
```

### Delete Policy

Delete a policy from a policy engine.

```
agentcore policy delete-policy [OPTIONS]
```

Options:

- `--policy-engine-id, -e TEXT`: Policy engine ID (required)
- `--policy-id, -p TEXT`: Policy ID (required)
- `--region, -r TEXT`: AWS region (defaults to us-east-1)

**Example:**

```
agentcore policy delete-policy \
  --policy-engine-id "testPolicyEngine-abc123" \
  --policy-id "policy-xyz789"
```

### Start Policy Generation

Policy generation requires a policy engine and gateway. Create the engine first to manage policies, then generate Cedar statements from natural language that target your gateway resource.

Generate Cedar policies from natural language descriptions.

```
agentcore policy start-policy-generation [OPTIONS]
```

Options:

- `--policy-engine-id, -e TEXT`: Policy engine ID (required)
- `--name, -n TEXT`: Generation name (required) - Must match pattern `^[A-Za-z][A-Za-z0-9_]*$` (letters, numbers, underscores only; must start with a letter)
- `--resource-arn TEXT`: Gateway ARN that the generated policies will target (required)
- `--content, -c TEXT`: Natural language policy description (required)
- `--region, -r TEXT`: AWS region (defaults to us-east-1)

**Note:** Policy generation typically completes within 30 seconds.

**Name Validation:**

- ✅ Valid: `refund_policy`, `MyPolicy123`, `policy_v1`
- ❌ Invalid: `refund-policy` (hyphens not allowed), `123policy` (must start with letter), `my.policy` (dots not allowed)

**Workflow:**

After starting generation, poll the generation status until complete, then list the generated policy assets.

**Example:**

```
# 0. Create policy engine (one-time setup)
agentcore policy create-policy-engine \
  --name "RefundPolicyEngine" \
  --region us-west-2

# 1. Start policy generation (note: use underscores, not hyphens in name)
agentcore policy start-policy-generation \
  --policy-engine-id "RefundEngine-a1b2c3d4e5" \
  --name "refund_limit_gen" \
  --resource-arn "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/gw-abc123" \
  --content "Allow refunds under $1000" \
  --region us-west-2
```

Output:

```
✓ Policy generation initiated!
Generation ID: refund_limit_gen-x9y8z7w6v5
Status: GENERATING
Name: refund_limit_gen
Use 'get-policy-generation' to check progress
ARN: arn:aws:bedrock-agentcore:us-west-2:123456789012:policy-engine/RefundEngine-a1b2c3d4e5/policy-generation/refund-limit-gen-x9y8z7w6v5
```

```
# 2. Poll generation status (repeat until status is GENERATED)
agentcore policy get-policy-generation \
  --policy-engine-id "RefundEngine-a1b2c3d4e5" \
  --generation-id "refund_limit_gen-x9y8z7w6v5" \
  --region us-west-2
```

Output when complete:

```
Policy Generation Details:
Generation ID: refund_limit_gen-x9y8z7w6v5
Name: refund_limit_gen
Status: GENERATED
ARN: arn:aws:bedrock-agentcore:us-west-2:123456789012:policy-engine/RefundEngine-a1b2c3d4e5/policy-generation/refund-limit-gen-x9y8z7w6v5
Created: 2025-03-15T10:30:00Z
Updated: 2025-03-15T10:30:22Z
```

```
# 3. List generated policy assets
agentcore policy list-policy-generation-assets \
  --policy-engine-id "RefundEngine-a1b2c3d4e5" \
  --generation-id "refund_limit_gen-x9y8z7w6v5" \
  --region us-west-2
```

Output:

```
{
  "policyGenerationAssets": [
    {
      "policyGenerationAssetId": "asset-m1n2o3p4q5",
      "definition": {
        "cedar": {
          "statement": "permit(principal, action == AgentCore::Action::\"RefundTarget___process_refund\", resource == AgentCore::Gateway::\"arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/gw-abc123\") when { context.input.amount < 1000 };"
        }
      },
      "rawTextFragment": "Allow refunds under $1000",
      "findings": [
        {
          "type": "VALID",
          "description": "Policy is syntactically valid"
        }
      ]
    }
  ]
}
```

You can now create a policy using the generated Cedar statement from the `definition.cedar.statement` field.

### Get Policy Generation

Get the status and details of a policy generation.

```
agentcore policy get-policy-generation [OPTIONS]
```

Options:

- `--policy-engine-id, -e TEXT`: Policy engine ID (required)
- `--generation-id, -g TEXT`: Generation ID (required)
- `--region, -r TEXT`: AWS region (defaults to us-east-1)

**Example:**

```
agentcore policy get-policy-generation \
  --policy-engine-id "testPolicyEngine-abc123" \
  --generation-id "gen-abc123"
```

### List Policy Generation Assets

List the generated policies from a policy generation.

```
agentcore policy list-policy-generation-assets [OPTIONS]
```

Options:

- `--policy-engine-id, -e TEXT`: Policy engine ID (required)
- `--generation-id, -g TEXT`: Generation ID (required)
- `--region, -r TEXT`: AWS region (defaults to us-east-1)
- `--max-results INTEGER`: Maximum number of results (optional)
- `--next-token TEXT`: Token for pagination (optional)

**Example:**

```
agentcore policy list-policy-generation-assets \
  --policy-engine-id "testPolicyEngine-abc123" \
  --generation-id "gen-abc123"
```

### List Policy Generations

List all policy generations in a policy engine.

```
agentcore policy list-policy-generations [OPTIONS]
```

Options:

- `--policy-engine-id, -e TEXT`: Policy engine ID (required)
- `--region, -r TEXT`: AWS region (defaults to us-east-1)
- `--max-results INTEGER`: Maximum number of results (optional)
- `--next-token TEXT`: Token for pagination (optional)

**Example:**

```
agentcore policy list-policy-generations \
  --policy-engine-id "testPolicyEngine-abc123" \
  --max-results 20
```

## Example Usage

### Configure an Agent

```
# Interactive configuration with memory prompts
agentcore configure --entrypoint agent_example.py

# Configure without memory
agentcore configure --entrypoint agent_example.py --disable-memory

# Configure with execution role
agentcore configure --entrypoint agent_example.py --execution-role arn:aws:iam::123456789012:role/MyRole

# Configure with VPC networking
agentcore configure \
  --entrypoint agent_example.py \
  --vpc \
  --subnets subnet-0abc123,subnet-0def456 \
  --security-groups sg-0xyz789

# Configure with VPC and custom execution role
agentcore configure \
  --entrypoint agent_example.py \
  --execution-role arn:aws:iam::123456789012:role/MyAgentRole \
  --vpc \
  --subnets subnet-0abc123,subnet-0def456,subnet-0ghi789 \
  --security-groups sg-0xyz789,sg-0uvw012

# Non-interactive with defaults
agentcore configure --entrypoint agent_example.py --non-interactive

# Configure with lifecycle management
agentcore configure --entrypoint agent_example.py \
  --idle-timeout 1800 \
  --max-lifetime 7200

# Configure with all options
agentcore configure --entrypoint agent_example.py \
  --execution-role arn:aws:iam::123456789012:role/MyRole \
  --idle-timeout 1800 \
  --max-lifetime 7200 \
  --region us-east-1

# List configured agents
agentcore configure list

# Set default agent
agentcore configure set-default my_agent
```

### Deploy and Run Agents

```
# Deploy to AWS (default - uses CodeBuild)
agentcore deploy

# Run locally
agentcore deploy --local

# Build locally, deploy to cloud
agentcore deploy --local-build

# Deploy with environment variables
agentcore deploy --env API_KEY=abc123 --env DEBUG=true

# Auto-update if agent exists
agentcore deploy --auto-update-on-conflict
```

### Invoke Agents

```
# Basic invocation
agentcore invoke '{"prompt": "Hello world!"}'

# Invoke with session ID
agentcore invoke '{"prompt": "Continue our conversation"}' --session-id abc123

# Invoke with OAuth authentication
agentcore invoke '{"prompt": "Secure request"}' --bearer-token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Invoke with custom headers
agentcore invoke '{"prompt": "Test"}' --headers "Actor-Id:user123,Trace-Id:abc"

# Invoke local agent
agentcore invoke '{"prompt": "Test locally"}' --local
```

### Check Status

```
# Get status of default agent
agentcore status

# Get status of specific agent
agentcore status --agent my-agent

# Verbose output with full JSON
agentcore status --verbose
```

### Destroy Resources

```
# Preview destruction
agentcore destroy --dry-run

# Destroy with confirmation
agentcore destroy

# Destroy specific agent without confirmation
agentcore destroy --agent my-agent --force
```

### Gateway Operations

```
# Create MCP Gateway
agentcore gateway create-mcp-gateway --name MyGateway

# Create MCP Gateway Target
agentcore gateway create-mcp-gateway-target \
  --gateway-arn arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/abcdef \
  --gateway-url https://gateway-url.us-west-2.amazonaws.com \
  --role-arn arn:aws:iam::123456789012:role/GatewayRole

# List all gateways
agentcore gateway list-mcp-gateways

# Get gateway details
agentcore gateway get-mcp-gateway --name MyGateway

# List gateway targets
agentcore gateway list-mcp-gateway-targets --name MyGateway

# Get target details
agentcore gateway get-mcp-gateway-target --name MyGateway --target-name MyTarget

# Delete a target
agentcore gateway delete-mcp-gateway-target --name MyGateway --target-name MyTarget

# Delete a gateway (must have no targets)
agentcore gateway delete-mcp-gateway --name MyGateway

# Delete a gateway and all its targets
agentcore gateway delete-mcp-gateway --name MyGateway --force
```

### Memory Operations

```
# Create memory with STM only
agentcore memory create my_agent_memory

# Create memory with LTM strategies
agentcore memory create my_memory \
  --strategies '[{"semanticMemoryStrategy": {"name": "Facts"}}]' \
  --description "Agent memory for customer service" \
  --event-expiry-days 90 \
  --wait

# List all memories
agentcore memory list

# Get memory details
agentcore memory get my_memory_abc123

# Check memory status
agentcore memory status my_memory_abc123

# Delete memory
agentcore memory delete my_memory_abc123 --wait
```

### Policy Operations

```
# Create a policy engine
agentcore policy create-policy-engine \
  --name "RefundPolicyEngine" \
  --description "Policy engine to regulate refund operations" \
  --region us-west-2

# List all policy engines
agentcore policy list-policy-engines --region us-west-2

# Get policy engine details
agentcore policy get-policy-engine \
  --policy-engine-id "testPolicyEngine-abc123" \
  --region us-west-2

# Create a Cedar policy
agentcore policy create-policy \
  --policy-engine-id "testPolicyEngine-abc123" \
  --name "refund_limit_policy" \
  --description "Allow refunds under $1000" \
  --definition '{"cedar":{"statement":"permit(principal, action == AgentCore::Action::\"RefundTarget___process_refund\", resource == AgentCore::Gateway::\"arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/my-gateway\") when { context.input.amount < 1000 };"}}' \
  --region us-west-2

# List policies in engine
agentcore policy list-policies \
  --policy-engine-id "testPolicyEngine-abc123" \
  --region us-west-2

# Get policy details
agentcore policy get-policy \
  --policy-engine-id "testPolicyEngine-abc123" \
  --policy-id "policy-xyz789" \
  --region us-west-2

# Update policy with new limit
agentcore policy update-policy \
  --policy-engine-id "testPolicyEngine-abc123" \
  --policy-id "policy-xyz789" \
  --definition '{"cedar":{"statement":"permit(principal, action == AgentCore::Action::\"RefundTarget___process_refund\", resource == AgentCore::Gateway::\"arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/my-gateway\") when { context.input.amount < 500 };"}}' \
  --description "Updated to $500 limit" \
  --region us-west-2

# Generate policy from natural language (use underscores in name)
agentcore policy start-policy-generation \
  --policy-engine-id "testPolicyEngine-abc123" \
  --name "refund_policy_generation" \
  --resource-arn "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/my-gateway" \
  --content "Allow refunds for amounts less than $1000" \
  --region us-west-2

# Check generation status
agentcore policy get-policy-generation \
  --policy-engine-id "testPolicyEngine-abc123" \
  --generation-id "gen-abc123" \
  --region us-west-2

# List generated policy assets
agentcore policy list-policy-generation-assets \
  --policy-engine-id "testPolicyEngine-abc123" \
  --generation-id "gen-abc123" \
  --region us-west-2

# List all policy generations
agentcore policy list-policy-generations \
  --policy-engine-id "testPolicyEngine-abc123" \
  --region us-west-2

# Delete a policy
agentcore policy delete-policy \
  --policy-engine-id "testPolicyEngine-abc123" \
  --policy-id "policy-xyz789" \
  --region us-west-2

# Delete policy engine
agentcore policy delete-policy-engine \
  --policy-engine-id "testPolicyEngine-abc123" \
  --region us-west-2
```

### Complete Policy Workflow with Gateway

```
# 1. Create gateway
agentcore gateway create-mcp-gateway \
  --name "RefundGateway" \
  --region us-west-2

# 2. Add Lambda target to gateway
agentcore gateway create-mcp-gateway-target \
  --gateway-arn "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/abc123" \
  --gateway-url "https://gateway.us-west-2.amazonaws.com" \
  --role-arn "arn:aws:iam::123456789012:role/GatewayRole" \
  --name "RefundTarget" \
  --target-type lambda \
  --region us-west-2

# 3. Create policy engine
agentcore policy create-policy-engine \
  --name "RefundPolicyEngine" \
  --description "Governance for refund operations" \
  --region us-west-2

# 4. Generate policy from natural language
agentcore policy start-policy-generation \
  --policy-engine-id "testPolicyEngine-abc123" \
  --name "refund_policy_gen" \
  --resource-arn "arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/abc123" \
  --content "Allow refunds under \$1000" \
  --region us-west-2

# 5. Wait and check generation (poll until GENERATED, typically ~20-30 seconds)
agentcore policy get-policy-generation \
  --policy-engine-id "testPolicyEngine-abc123" \
  --generation-id "refund_policy_gen-xyz789" \
  --region us-west-2

# 6. Review generated policies
agentcore policy list-policy-generation-assets \
  --policy-engine-id "testPolicyEngine-abc123" \
  --generation-id "refund_policy_gen-xyz789" \
  --region us-west-2

# 7. Create policy from generated asset (or use your own)
agentcore policy create-policy \
  --policy-engine-id "testPolicyEngine-abc123" \
  --name "refund_limit_policy" \
  --description "Allow refunds under \$1000" \
  --definition '{"cedar":{"statement":"permit(principal, action == AgentCore::Action::\"RefundTarget___process_refund\", resource == AgentCore::Gateway::\"arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/abc123\") when { context.input.amount < 1000 };"}}' \
  --region us-west-2

# 8. Policies are now enforced at gateway runtime
# Test via agent invocation with gateway
```

### Importing from Bedrock Agents

```
# Interactive Mode
agentcore import-agent

# For Automation
agentcore import-agent \
  --region us-east-1 \
  --agent-id ABCD1234 \
  --agent-alias-id TSTALIASID \
  --target-platform strands \
  --output-dir ./my-agent \
  --deploy-runtime \
  --run-option runtime

# AgentCore Primitive Opt-out
agentcore import-agent --disable-gateway --disable-memory --disable-code-interpreter --disable-observability
```

## Memory Best Practices

### Agent Code Pattern

When using memory in agent code, conditionally create memory configuration:

```
import os
from bedrock_agentcore.memory.integrations.strands.config import AgentCoreMemoryConfig
from bedrock_agentcore.memory.integrations.strands.session_manager import AgentCoreMemorySessionManager

MEMORY_ID = os.getenv("BEDROCK_AGENTCORE_MEMORY_ID")
REGION = os.getenv("AWS_REGION")

@app.entrypoint
def invoke(payload, context):
    # Only create memory config if MEMORY_ID exists
    session_manager = None
    if MEMORY_ID:
        memory_config = AgentCoreMemoryConfig(
            memory_id=MEMORY_ID,
            session_id=context.session_id,
            actor_id=context.actor_id
        )
        session_manager = AgentCoreMemorySessionManager(memory_config, REGION)

    agent = Agent(
        model="...",
        session_manager=session_manager,  # None when memory disabled
        ...
    )
```
