# CLI

Command-line interface for BedrockAgentCore Starter Toolkit.

The `agentcore` CLI provides commands for configuring, launching, managing agents, and working with gateways.


## Runtime Commands

### Configure

Configure agents and runtime environments.

```bash
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

```bash
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

```bash
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

```bash
# Configure with lifecycle settings
agentcore configure --entrypoint agent.py \
  --idle-timeout 1800 \    # 30 minutes idle before termination
  --max-lifetime 7200      # 2 hours max regardless of activity
```

### Launch

Deploy agents to AWS or run locally.

```bash
agentcore launch [OPTIONS]
```

Options:

- `--agent, -a TEXT`: Agent name

- `--local, -l`: Build and run locally (requires Docker/Finch/Podman)

- `--local-build, -lb`: Build locally and deploy to cloud (requires Docker/Finch/Podman)

- `--auto-update-on-conflict, -auc`: Automatically update existing agent instead of failing

- `--env, -env TEXT`: Environment variables for agent (format: KEY=VALUE)

**Deployment Modes:**

```bash
# CodeBuild (default) - Cloud build, no Docker required
agentcore launch

# Local mode - Build and run locally
agentcore launch --local

# Local build mode - Build locally, deploy to cloud
agentcore launch --local-build
```

**Memory Provisioning:**

During launch, if memory is enabled:

- Memory resources are created and provisioned
- Launch waits for memory to become ACTIVE before proceeding
- STM provisioning: ~30-90 seconds
- LTM provisioning: ~120-180 seconds
- Progress updates displayed during wait

### Invoke

Invoke deployed agents.

```bash
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

```bash
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

```bash
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

```bash
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

```bash
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

```bash
agentcore stop-session [OPTIONS]
```

**Session Tracking:**

The CLI automatically tracks the runtime session ID from the last `agentcore invoke` command. This allows you to stop sessions without manually specifying the session ID.

**Examples:**

```bash
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

```bash
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

```bash
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

```bash
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

**Discovery URL Format:**
Must be the complete OIDC discovery URL including `.well-known/openid-configuration`:

```bash
# Cognito format
https://cognito-idp.us-west-2.amazonaws.com/us-west-2_xxxxx/.well-known/openid-configuration
```

**Automatic Configuration:**

- Creates the credential provider in AgentCore Identity
- Adds provider configuration to `.bedrock_agentcore.yaml`
- IAM permissions added automatically during `agentcore launch`

**Note:** After creating a provider, you must register the returned `callbackUrl` in your OAuth provider’s settings (except for Cognito, which is auto-configured with `--cognito-pool-id`).

**Examples:**

```bash
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

```bash
agentcore identity create-workload-identity [OPTIONS]
```

Options:

- `--name TEXT`: Workload identity name (auto-generated if not provided)
- `--region TEXT`: AWS region (defaults to configured region)

**Example:**

```bash
agentcore identity create-workload-identity --name my-workload
```

### Get Cognito Inbound Token

Generate a JWT bearer token from Cognito for Runtime inbound authentication.

Automatically loads credentials from environment variables. Explicit parameters override environment variables.

```bash
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

```bash
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

```bash
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
- Configuration files (.agentcore_identity_*)

**Example:**

```bash
# Clean up with confirmation
agentcore identity cleanup --agent my-agent

# Clean up without prompts
agentcore identity cleanup --agent my-agent --force
```

## Identity Example Usage

### Complete Identity Setup Workflow

```bash
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
agentcore launch

# 7. Get bearer token for Runtime auth
TOKEN=$(agentcore identity get-cognito-inbound-token)

# 8. Invoke with JWT authentication
agentcore invoke '{"prompt": "Call external service"}' \
  --bearer-token "$TOKEN" \
  --session-id "demo_session_$(uuidgen | tr -d '-')"

# 9. Cleanup when done
agentcore identity cleanup --agent my-agent --force
```

## Gateway Commands

Access gateway subcommands:

```bash
agentcore gateway [COMMAND]
```

### Create MCP Gateway

```bash
agentcore gateway create-mcp-gateway [OPTIONS]
```

Options:

- `--region TEXT`: Region to use (defaults to us-west-2)

- `--name TEXT`: Name of the gateway (defaults to TestGateway)

- `--role-arn TEXT`: Role ARN to use (creates one if none provided)

- `--authorizer-config TEXT`: Serialized authorizer config

- `--enable-semantic-search, -sem`: Whether to enable search tool (defaults to True)

### Create MCP Gateway Target

```bash
agentcore gateway create-mcp-gateway-target [OPTIONS]
```

Options:

- `--gateway-arn TEXT`: ARN of the created gateway

- `--gateway-url TEXT`: URL of the created gateway

- `--role-arn TEXT`: Role ARN of the created gateway

- `--region TEXT`: Region to use (defaults to us-west-2)

- `--name TEXT`: Name of the target (defaults to TestGatewayTarget)

- `--target-type TEXT`: Type of target (lambda, openApiSchema, smithyModel)

- `--target-payload TEXT`: Specification of the target (required for openApiSchema)

- `--credentials TEXT`: Credentials for calling this target (API key or OAuth2)

## Example Usage

### Configure an Agent

```bash
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

```bash
# Deploy to AWS (default - uses CodeBuild)
agentcore launch

# Run locally
agentcore launch --local

# Build locally, deploy to cloud
agentcore launch --local-build

# Launch with environment variables
agentcore launch --env API_KEY=abc123 --env DEBUG=true

# Auto-update if agent exists
agentcore launch --auto-update-on-conflict
```

### Invoke Agents

```bash
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

```bash
# Get status of default agent
agentcore status

# Get status of specific agent
agentcore status --agent my-agent

# Verbose output with full JSON
agentcore status --verbose
```

### Destroy Resources

```bash
# Preview destruction
agentcore destroy --dry-run

# Destroy with confirmation
agentcore destroy

# Destroy specific agent without confirmation
agentcore destroy --agent my-agent --force
```

### Gateway Operations

```bash
# Create MCP Gateway
agentcore gateway create-mcp-gateway --name MyGateway

# Create MCP Gateway Target
agentcore gateway create-mcp-gateway-target \
  --gateway-arn arn:aws:bedrock-agentcore:us-west-2:123456789012:gateway/abcdef \
  --gateway-url https://gateway-url.us-west-2.amazonaws.com \
  --role-arn arn:aws:iam::123456789012:role/GatewayRole
```

### Importing from Bedrock Agents

```bash
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

```python
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
