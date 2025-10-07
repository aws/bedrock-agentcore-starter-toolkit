# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Package Overview

**Bedrock AgentCore Starter Toolkit** is a CLI-based deployment and management toolkit for Amazon Bedrock AgentCore. It automates the entire agent deployment lifecycle: containerization, AWS resource provisioning (ECR, IAM, CodeBuild), and agent deployment to Bedrock AgentCore Runtime.

**Key Capabilities**:
- Interactive CLI for agent configuration and deployment
- Automated AWS resource management (ECR repositories, IAM roles, CodeBuild projects)
- Docker containerization with optimized ARM64 builds
- Agent lifecycle management (configure, launch, invoke, status, destroy)
- Gateway (MCP) and Memory service integrations
- Import Bedrock Agents to AgentCore
- Observability integration (X-Ray, CloudWatch)

**Related Package**: Works with [bedrock-agentcore SDK](../bedrock-agentcore-sdk-python/CLAUDE.md) which provides the runtime framework for building agents.

## Development Setup

### Prerequisites
- Python 3.10-3.13
- uv package manager
- AWS credentials configured
- Docker (for local container testing)

### Environment Setup
```bash
# Install dependencies and create virtual environment
uv sync

# Install in development mode
uv pip install -e .

# Verify CLI installation
agentcore --help
```

## Architecture Overview

### Three-Layer Architecture

The toolkit follows a clean three-layer architecture pattern:

```
┌─────────────────────────────────────────┐
│           CLI Layer                     │  User-facing commands (Typer)
│  src/bedrock_agentcore_starter_toolkit/ │
│  └── cli/                               │
│      ├── cli.py (entry point)           │
│      ├── runtime/commands.py            │
│      ├── gateway/commands.py            │
│      └── import_agent/commands.py       │
└─────────────────────────────────────────┘
              ↓ calls
┌─────────────────────────────────────────┐
│       Operations Layer                  │  Business logic & orchestration
│  └── operations/                        │
│      ├── runtime/                       │  Launch, configure, destroy, invoke, status
│      ├── gateway/                       │  Gateway operations
│      └── memory/                        │  Memory operations
└─────────────────────────────────────────┘
              ↓ calls
┌─────────────────────────────────────────┐
│        Services Layer                   │  AWS service abstractions
│  └── services/                          │
│      ├── codebuild.py                   │  CodeBuild project management
│      ├── ecr.py                         │  ECR repository operations
│      ├── runtime.py                     │  Bedrock AgentCore Runtime client
│      ├── xray.py                        │  X-Ray observability
│      └── import_agent/                  │  Import agent services
└─────────────────────────────────────────┘
              ↓ uses
┌─────────────────────────────────────────┐
│         Utilities Layer                 │  Shared utilities
│  └── utils/                             │
│      ├── runtime/                       │  Config, container, entrypoint, logs
│      │   ├── config.py                  │  YAML config management
│      │   ├── schema.py                  │  Pydantic models
│      │   ├── container.py               │  Docker operations
│      │   ├── entrypoint.py              │  Entrypoint validation
│      │   ├── logs.py                    │  CloudWatch/observability
│      │   └── templates/                 │  Jinja2 templates
│      └── endpoints.py                   │  AWS endpoint URLs
└─────────────────────────────────────────┘
```

### Layer Responsibilities

**CLI Layer** (`cli/`):
- User input validation and prompts (prompt-toolkit, questionary)
- Rich console output formatting
- Command routing and argument parsing (Typer)
- Error handling and user-friendly messages
- **Pattern**: Commands delegate to operations layer, handle display only

**Operations Layer** (`operations/`):
- Workflow orchestration (multi-step deployment processes)
- Idempotent resource management (check-then-create patterns)
- Configuration updates and persistence
- Cross-service coordination
- **Pattern**: Orchestrates services, updates config, implements business logic

**Services Layer** (`services/`):
- AWS SDK wrappers (boto3)
- Service-specific error handling
- Resource CRUD operations
- **Pattern**: Thin wrappers over AWS APIs, single responsibility per service

**Utilities Layer** (`utils/`):
- Configuration serialization (YAML ↔ Pydantic models)
- Docker operations (build, run, exec)
- Template rendering (Jinja2)
- Endpoint URL management
- **Pattern**: Pure functions, no AWS API calls

## Key Development Patterns

### 1. Idempotent Resource Management

All resource creation operations follow the check-then-create pattern:

```python
# Example from operations/runtime/launch.py
def _ensure_ecr_repository(agent_config, project_config, config_path, agent_name, region):
    """Ensure ECR repository exists (idempotent)."""
    # Step 1: Check config first
    if agent_config.aws.ecr_repository:
        log.info("Using ECR repository from config: %s", ecr_uri)
        return ecr_uri

    # Step 2: Create if needed (and auto-create enabled)
    if agent_config.aws.ecr_auto_create:
        ecr_uri = get_or_create_ecr_repository(agent_name, region)

        # Step 3: Persist to config
        agent_config.aws.ecr_repository = ecr_uri
        agent_config.aws.ecr_auto_create = False
        save_config(project_config, config_path)

        return ecr_uri

    raise ValueError("ECR repository not configured and auto-create not enabled")
```

**Key Pattern**: Check config → Check AWS → Create if needed → Update config

### 2. Configuration Management

Configuration is managed through `utils/runtime/config.py` with Pydantic models:

```python
# Load configuration with legacy format support
config = load_config(Path.cwd() / ".bedrock_agentcore.yaml")

# Access agent config
agent_config = config.agents[config.default_agent]

# Update and persist
agent_config.bedrock_agentcore.agent_arn = new_arn
save_config(config, config_path)
```

**Key Files**:
- `utils/runtime/schema.py` - Pydantic models (BedrockAgentCoreConfigSchema, BedrockAgentCoreAgentSchema)
- `utils/runtime/config.py` - Load/save operations, legacy format transformation

**Config File Location**: `.bedrock_agentcore.yaml` at project root

### 3. CLI Error Handling Pattern

Consistent error handling across all CLI commands:

```python
from ..common import _handle_error, _print_success, console

# Success
_print_success(f"Agent deployed: {agent_arn}")

# Error (exits with code 1)
_handle_error("ECR repository not configured", exception)

# Warning
_handle_warn("Memory service unavailable")
```

### 4. Rich Console Output

Use Rich library for formatted output:

```python
from rich.panel import Panel
from ..common import console

console.print(Panel(
    "Configuration complete!",
    title="✅ Success",
    border_style="green"
))
```

### 5. Service Client Pattern

Services are initialized with boto3.Session for testability:

```python
class CodeBuildService:
    def __init__(self, session: boto3.Session):
        self.session = session
        self.client = session.client("codebuild")
        self.s3_client = session.client("s3")
        self.logger = logging.getLogger(__name__)
```

### 6. Template Rendering

Jinja2 templates in `utils/runtime/templates/`:

```python
from jinja2 import Environment, FileSystemLoader

template_dir = Path(__file__).parent / "templates"
env = Environment(loader=FileSystemLoader(template_dir))
template = env.get_template("Dockerfile.j2")

rendered = template.render(
    python_version="3.10",
    aws_region=region,
    dependencies_file="requirements.txt"
)
```

**Templates**:
- `Dockerfile.j2` - Agent container image
- `execution_role_policy.json.j2` - IAM policies for Runtime execution role
- `execution_role_trust_policy.json.j2` - IAM trust policies

## Configuration File Schema

### .bedrock_agentcore.yaml Structure

```yaml
default_agent: my-agent-name     # Default agent for commands

agents:
  my-agent-name:
    name: my-agent-name
    entrypoint: agent_example.py
    platform: linux/arm64
    container_runtime: none      # 'none' (cloud) or 'docker' (local)

    aws:
      execution_role: arn:aws:iam::...:role/...
      execution_role_auto_create: false
      account: '123456789012'
      region: us-west-2
      ecr_repository: 123456789012.dkr.ecr.us-west-2.amazonaws.com/...
      ecr_auto_create: false
      network_configuration:
        network_mode: PUBLIC     # PUBLIC or VPC
      protocol_configuration:
        server_protocol: HTTP    # HTTP or HTTPS
      observability:
        enabled: true            # X-Ray tracing

    bedrock_agentcore:
      agent_id: my-agent-name-xyz123
      agent_arn: arn:aws:bedrock-agentcore:us-west-2:...:runtime/...
      agent_session_id: null

    codebuild:
      project_name: bedrock-agentcore-my-agent-name-builder
      execution_role: arn:aws:iam::...:role/...
      source_bucket: bedrock-agentcore-codebuild-sources-...

    memory:                      # Optional memory configuration
      is_enabled: true
      has_ltm: true              # Long-term memory
      memory_id: null
      memory_name: null

    authorizer_configuration: null   # Optional JWT authorizer
    request_header_configuration: null
    oauth_configuration: null
```

### Configuration Lifecycle

1. **Initial creation**: `agentcore configure` creates config with defaults
2. **Auto-update**: Operations update config with created resource ARNs/IDs
3. **Persistence**: All updates immediately saved to disk
4. **Validation**: Pydantic models validate on load
5. **Legacy support**: Old single-agent format auto-transforms to multi-agent format

## CLI Commands Reference

### Core Agent Lifecycle

```bash
# Configuration
agentcore configure                         # Interactive wizard
agentcore configure --entrypoint agent.py --name my-agent --region us-west-2
agentcore configure list                    # List all agents
agentcore configure set-default <name>      # Set default agent

# Deployment
agentcore launch                            # Deploy agent to cloud
agentcore launch --agent-name my-agent      # Deploy specific agent

# Testing
agentcore invoke '{"prompt": "hello"}'      # Invoke deployed agent
agentcore invoke --payload payload.json     # Invoke with file

# Monitoring
agentcore status                            # Check deployment status
agentcore status --agent-name my-agent      # Check specific agent

# Cleanup
agentcore destroy                           # Delete agent and resources
agentcore destroy --agent-name my-agent     # Destroy specific agent
```

### Gateway (MCP) Commands

```bash
agentcore create_mcp_gateway                # Create MCP gateway
agentcore create_mcp_gateway_target         # Create gateway target
agentcore gateway <subcommands>             # Gateway management
```

### Import Agent

```bash
agentcore import-agent                      # Import Bedrock Agent to AgentCore
```

### Development Commands

```bash
# Run CLI directly (useful for debugging)
uv run python -m bedrock_agentcore_starter_toolkit.cli.cli configure
uv run python -m bedrock_agentcore_starter_toolkit.cli.cli launch

# CLI entry point is installed as 'agentcore'
agentcore --help
```

## Deployment Workflow Deep Dive

### agentcore launch - Step by Step

The launch operation (`operations/runtime/launch.py`) orchestrates the full deployment:

```
1. Load Configuration
   └─ load_config(.bedrock_agentcore.yaml)

2. Ensure ECR Repository (Idempotent)
   ├─ Check config for existing repository
   ├─ If auto_create: get_or_create_ecr_repository()
   └─ Save ECR URI to config

3. Ensure IAM Execution Roles (Idempotent)
   ├─ Runtime execution role (bedrock-agentcore.amazonaws.com trust)
   ├─ CodeBuild execution role (codebuild.amazonaws.com trust)
   └─ Save role ARNs to config

4. Ensure Memory (Optional, Idempotent)
   ├─ Check if memory enabled in config
   ├─ Create memory resource if needed
   ├─ Configure strategies (LTM, STM)
   └─ Save memory_id to config

5. Package Source Code
   ├─ Parse .dockerignore patterns
   ├─ Create source.zip (respecting ignore patterns)
   └─ Upload to S3: s3://bucket/agent-name/source.zip

6. Create/Update CodeBuild Project (Idempotent)
   ├─ Check for existing project
   ├─ Generate ARM64 buildspec
   ├─ Create or update project config
   └─ Configuration: BUILD_GENERAL1_MEDIUM, ARM64

7. Trigger CodeBuild Build
   ├─ Start build with source location
   ├─ Monitor build progress (logs)
   ├─ Wait for completion (Docker build + ECR push)
   └─ Extract ECR image tag from logs

8. Deploy to Bedrock AgentCore Runtime
   ├─ Check if agent exists (get_agent_runtime)
   ├─ Create new: create_agent_runtime()
   │  └─ Or update existing: update_agent_runtime()
   ├─ Wait for READY status
   └─ Save agent_id and agent_arn to config

9. Enable Observability (Optional)
   ├─ Enable X-Ray transaction search
   └─ Display CloudWatch/X-Ray URLs

10. Display Results
    ├─ Agent ARN
    ├─ Observability URLs
    └─ Next steps (invoke command)
```

### Resource Creation Patterns

**ECR Repository** (`services/ecr.py`):
- Name: `bedrock-agentcore-{agent-name}`
- Auto-created if `ecr_auto_create: true`
- Idempotent: checks existence before creating

**IAM Roles** (`operations/runtime/create_role.py`):
- Runtime role: `AmazonBedrockAgentCoreSDKRuntime-{region}-{random_id}`
- CodeBuild role: `AmazonBedrockAgentCoreSDKCodeBuild-{region}-{random_id}`
- Policies rendered from Jinja2 templates
- Idempotent with existence checks

**CodeBuild Project** (`services/codebuild.py`):
- Name: `bedrock-agentcore-{agent-name}-builder`
- Platform: ARM64 Linux (BUILD_GENERAL1_MEDIUM)
- Source: S3 bucket with 7-day lifecycle policy
- Idempotent: updates project if exists

**S3 Source Bucket**:
- Name: `bedrock-agentcore-codebuild-sources-{account_id}-{region}`
- Lifecycle: Delete objects after 7 days
- Per-agent organization: `{agent-name}/source.zip`

## Testing Strategy

### Test Organization

```
tests/
├── conftest.py                 # Shared fixtures (boto3 mocks, subprocess mocks)
├── conftest_mock.py            # Additional mock utilities
├── cli/                        # CLI command tests
│   ├── test_common.py
│   └── runtime/
├── operations/                 # Operations layer tests
│   └── runtime/
├── services/                   # Service layer tests
│   ├── test_codebuild.py
│   ├── test_ecr.py
│   └── test_runtime.py
└── utils/                      # Utility tests
    ├── runtime/
    │   ├── test_config.py
    │   ├── test_container.py
    │   ├── test_entrypoint.py
    │   └── test_policy_template.py
    └── test_endpoints.py
```

### Testing Patterns

**1. AWS Service Mocking with pytest fixtures**:

```python
# conftest.py provides mock_boto3_clients fixture
def test_ecr_repository_creation(mock_boto3_clients):
    """Test ECR repository creation."""
    from bedrock_agentcore_starter_toolkit.services.ecr import get_or_create_ecr_repository

    result = get_or_create_ecr_repository("test-agent", "us-west-2")

    mock_boto3_clients["ecr"].create_repository.assert_called_once()
    assert "123456789012.dkr.ecr.us-west-2.amazonaws.com" in result
```

**2. Configuration Testing**:

```python
def test_load_config(tmp_path):
    """Test configuration loading."""
    config_file = tmp_path / ".bedrock_agentcore.yaml"
    config_file.write_text("""
default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: agent.py
""")

    config = load_config(config_file)
    assert config.default_agent == "test-agent"
    assert "test-agent" in config.agents
```

**3. Template Rendering Tests**:

```python
def test_dockerfile_template():
    """Test Dockerfile template rendering."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("Dockerfile.j2")

    rendered = template.render(python_version="3.10")
    assert "FROM ghcr.io/astral-sh/uv:python3.10" in rendered
```

### Running Tests

```bash
# All tests
uv run pytest tests/

# Specific test file
uv run pytest tests/services/test_codebuild.py

# With coverage (90% threshold required)
uv run pytest --cov=src --cov-report=term-missing --cov-branch tests/

# Pattern matching
uv run pytest -k "test_config"

# Verbose output
uv run pytest -v tests/
```

### Integration Tests

```
tests_integ/
├── runtime/              # End-to-end deployment tests
└── services/             # AWS service integration tests
```

Integration tests require AWS credentials and are typically run manually or in CI/CD.

## Common Development Tasks

### Adding a New CLI Command

1. **Create command in CLI layer** (`cli/runtime/commands.py`):
```python
@configure_app.command("new-command")
def new_command(
    agent_name: Optional[str] = typer.Option(None, "--agent-name"),
):
    """Description of new command."""
    try:
        config = load_config(Path.cwd() / ".bedrock_agentcore.yaml")
        # Delegate to operations layer
        result = perform_operation(config, agent_name)
        _print_success(f"Operation complete: {result}")
    except Exception as e:
        _handle_error(f"Failed: {str(e)}", e)
```

2. **Implement operation** (`operations/runtime/new_operation.py`):
```python
def perform_operation(config: BedrockAgentCoreConfigSchema, agent_name: str):
    """Implement business logic."""
    # Orchestrate services
    # Update configuration
    # Return results
    pass
```

3. **Add tests** (`tests/cli/runtime/test_commands.py`):
```python
def test_new_command(mock_boto3_clients, tmp_path):
    """Test new command."""
    # Setup
    # Execute
    # Assert
    pass
```

### Adding a New AWS Service Integration

1. **Create service client** (`services/new_service.py`):
```python
class NewServiceClient:
    def __init__(self, session: boto3.Session):
        self.session = session
        self.client = session.client("service-name")
        self.logger = logging.getLogger(__name__)

    def create_resource(self, name: str) -> str:
        """Create resource (idempotent)."""
        # Check existence
        # Create if needed
        # Return resource identifier
        pass
```

2. **Add operation** (`operations/runtime/new_operation.py`):
```python
from ...services.new_service import NewServiceClient

def ensure_resource(config, agent_name):
    """Ensure resource exists (idempotent)."""
    session = boto3.Session(region_name=config.aws.region)
    client = NewServiceClient(session)
    resource_id = client.create_resource(agent_name)
    return resource_id
```

3. **Update schema** (`utils/runtime/schema.py`):
```python
class BedrockAgentCoreAgentSchema(BaseModel):
    # ... existing fields ...
    new_service: Optional[NewServiceConfig] = None
```

4. **Add tests** with mocking:
```python
# conftest.py - add mock
mock_new_service = Mock()
mock_new_service.create_resource.return_value = "resource-123"

# tests/services/test_new_service.py
def test_create_resource(mock_boto3_clients):
    client = NewServiceClient(mock_boto3_clients["session"])
    result = client.create_resource("test-agent")
    assert result == "resource-123"
```

### Updating Configuration Schema

When adding new configuration fields:

1. **Update Pydantic models** (`utils/runtime/schema.py`):
```python
class BedrockAgentCoreAgentSchema(BaseModel):
    # ... existing fields ...
    new_field: Optional[str] = None
```

2. **Update configuration loading** if needed (`utils/runtime/config.py`)
3. **Add migration logic** for existing configs if breaking change
4. **Update tests** (`tests/utils/runtime/test_config.py`)
5. **Update documentation**

### Debugging Deployment Issues

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Check configuration
cat .bedrock_agentcore.yaml

# Verify AWS credentials
aws sts get-caller-identity

# Test ECR access
aws ecr describe-repositories --region us-west-2

# Check CodeBuild logs
aws codebuild list-builds-for-project \
  --project-name bedrock-agentcore-{agent-name}-builder

# Get build logs
aws logs tail /aws/codebuild/bedrock-agentcore-{agent-name}-builder --follow

# Check agent status
agentcore status

# Invoke with verbose output
agentcore invoke '{"prompt": "test"}' --debug
```

## Code Quality Standards

### Pre-commit Validation

**Always run before committing**:
```bash
uv run pre-commit run --all-files
```

Pre-commit hooks enforce:
- **uv-lock**: Dependency synchronization
- **ruff check**: Linting with auto-fix
- **ruff format**: Code formatting
- **mypy**: Strict type checking
- **bandit**: Security scanning
- **pytest**: Unit tests with 90% coverage threshold
- **File hygiene**: Trailing whitespace, JSON/TOML validation

### Type Checking

Strict MyPy configuration in `pyproject.toml`:
```toml
[tool.mypy]
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
```

All functions must have type annotations:
```python
def create_agent(name: str, region: str) -> str:
    """Create agent and return ARN."""
    pass
```

### Documentation Standards

Google-style docstrings required:
```python
def launch_agent(config: BedrockAgentCoreConfigSchema, agent_name: str) -> LaunchResult:
    """Deploy agent to Bedrock AgentCore Runtime.

    Args:
        config: Project configuration
        agent_name: Name of agent to deploy

    Returns:
        LaunchResult with agent ARN and deployment status

    Raises:
        ValueError: If agent not configured
        ClientError: If AWS operation fails
    """
    pass
```

### Linting Configuration

Ruff linting (120 char line length):
```toml
[tool.ruff.lint]
select = [
  "B",    # flake8-bugbear
  "D",    # pydocstyle
  "E",    # pycodestyle
  "F",    # pyflakes
  "G",    # logging format
  "I",    # isort
  "LOG",  # logging
]
```

### Test Coverage

**Required**: 90% coverage with branch coverage:
```bash
uv run pytest --cov=src --cov-report=term-missing --cov-branch tests/
```

Coverage exemptions in `pyproject.toml`:
```toml
[tool.coverage.run]
omit = [
    "src/bedrock_agentcore_starter_toolkit/cli/import_agent/*",
    "src/bedrock_agentcore_starter_toolkit/services/import_agent/utils.py",
]
```

## Quick Reference

### Essential Commands
```bash
# Setup
uv sync && uv pip install -e .

# Development cycle
uv run pytest --cov=src --cov-report=term-missing tests/
uv run mypy src/
uv run ruff check && uv run ruff format
uv run bandit -r src/

# Pre-commit (REQUIRED before committing)
uv run pre-commit run --all-files

# Build documentation
uv run mkdocs serve           # Local preview
uv run mkdocs build           # Static build

# CLI testing
agentcore configure --help
uv run python -m bedrock_agentcore_starter_toolkit.cli.cli launch
```

### Key File Locations

**CLI Layer**:
- Entry point: `src/bedrock_agentcore_starter_toolkit/cli/cli.py`
- Runtime commands: `src/bedrock_agentcore_starter_toolkit/cli/runtime/commands.py`
- Common utilities: `src/bedrock_agentcore_starter_toolkit/cli/common.py`

**Operations Layer**:
- Launch workflow: `src/bedrock_agentcore_starter_toolkit/operations/runtime/launch.py`
- Configure: `src/bedrock_agentcore_starter_toolkit/operations/runtime/configure.py`
- Destroy: `src/bedrock_agentcore_starter_toolkit/operations/runtime/destroy.py`
- Invoke: `src/bedrock_agentcore_starter_toolkit/operations/runtime/invoke.py`

**Services Layer**:
- CodeBuild: `src/bedrock_agentcore_starter_toolkit/services/codebuild.py`
- ECR: `src/bedrock_agentcore_starter_toolkit/services/ecr.py`
- Runtime: `src/bedrock_agentcore_starter_toolkit/services/runtime.py`

**Configuration**:
- Schema: `src/bedrock_agentcore_starter_toolkit/utils/runtime/schema.py`
- Config management: `src/bedrock_agentcore_starter_toolkit/utils/runtime/config.py`
- User config file: `.bedrock_agentcore.yaml` (project root)

**Templates**:
- Dockerfile: `src/bedrock_agentcore_starter_toolkit/utils/runtime/templates/Dockerfile.j2`
- IAM policies: `src/bedrock_agentcore_starter_toolkit/utils/runtime/templates/execution_role_*.json.j2`

**Tests**:
- Fixtures: `tests/conftest.py`
- CLI tests: `tests/cli/`
- Service tests: `tests/services/`
- Integration: `tests_integ/`

### Debugging Tips

**Enable verbose logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Inspect configuration**:
```python
from pathlib import Path
from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

config = load_config(Path(".bedrock_agentcore.yaml"))
print(config.model_dump_json(indent=2))
```

**Test AWS credentials**:
```bash
aws sts get-caller-identity
aws ecr describe-repositories --region us-west-2
```

**Manual resource inspection**:
```bash
# ECR
aws ecr describe-repositories --repository-names bedrock-agentcore-{agent-name}

# CodeBuild
aws codebuild list-projects
aws codebuild list-builds-for-project --project-name bedrock-agentcore-{agent-name}-builder

# IAM
aws iam get-role --role-name AmazonBedrockAgentCoreSDKRuntime-{region}-{id}

# Bedrock AgentCore Runtime
aws bedrock-agentcore list-agent-runtimes --region us-west-2
```

## Additional Resources

- **Documentation**: `documentation/docs/` - MkDocs source
- **MkDocs config**: `documentation/mkdocs.yaml`
- **Samples**: `../samples/` - Example agent implementations
- **SDK Documentation**: `../bedrock-agentcore-sdk-python/CLAUDE.md` - Runtime SDK guide
