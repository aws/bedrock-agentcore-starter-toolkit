# Data Model: Multi-Agent Configuration Safeguards

## Agent Configuration Entity

**Purpose**: Represents an individual agent's complete configuration and deployment state

**Attributes**:
- `name`: Unique identifier for the agent (string, required)
- `entrypoint`: Path to agent's main file (string, required)
- `source_path`: Directory containing agent source code (string, required)
- `platform`: Target deployment platform (string, default: "linux/arm64")
- `container_runtime`: Runtime environment (enum: "none", "docker")
- `aws_config`: AWS-specific deployment configuration (nested object)
- `bedrock_agentcore_config`: AgentCore Runtime deployment state (nested object)
- `codebuild_config`: Build pipeline configuration (nested object)
- `memory_config`: Optional memory service configuration (nested object)
- `build_artifacts`: Reference to isolated build artifacts (nested object)

**Validation Rules**:
- Name must be unique within project configuration
- Entrypoint file must exist and be accessible
- Source path must exist and contain valid agent code
- AWS account and region must be consistent across agent configurations

**State Transitions**:
- CONFIGURED → BUILDING → BUILT → DEPLOYED → READY
- READY → UPDATING → READY (for updates)
- READY → DESTROYING → DESTROYED (for cleanup)

## Configuration Directory Entity

**Purpose**: Represents the file system organization for storing agent configurations

**Attributes**:
- `base_path`: Root directory for all agent configurations (string)
- `agent_directories`: Map of agent names to their individual directories (map)
- `global_config_path`: Path to master configuration file (string)
- `shared_resources`: Common resources used by multiple agents (list)

**Relationships**:
- Contains multiple Agent Configuration entities
- References Build Artifact entities for each agent
- Maintains integrity with Global Configuration entity

## Global Configuration Entity

**Purpose**: Master registry tracking all configured agents and project-level settings

**Attributes**:
- `default_agent`: Name of the default agent for operations (string, optional)
- `agents`: Collection of agent configurations (map: name → AgentConfiguration)
- `project_metadata`: Project-level settings and constraints (nested object)
- `version`: Configuration schema version for migration support (string)

**Validation Rules**:
- Default agent must exist in agents collection if specified
- Agent names must be unique across the project
- All agent configurations must pass individual validation

## Build Artifact Entity

**Purpose**: Represents isolated deployment files created automatically during launch

**Attributes**:
- `agent_name`: Associated agent identifier (string, required)
- `build_directory`: Path to isolated build artifacts (string, required)
- `source_copy_path`: Path to copied source code (string, required)
- `dockerfile_path`: Path to generated Dockerfile (string, required)
- `build_timestamp`: When artifacts were created (datetime)
- `build_status`: Current status of build artifacts (enum: "pending", "ready", "failed")

**Lifecycle**:
- Created automatically during `agentcore launch`
- Cleaned up automatically during `agentcore destroy`
- Maintained separately for each agent to prevent conflicts

**Relationships**:
- Belongs to exactly one Agent Configuration
- Contains references to copied source files and generated deployment files

## Error Context Entity

**Purpose**: State information needed for error recovery including created resources

**Attributes**:
- `operation_id`: Unique identifier for the operation (string, required)
- `operation_type`: Type of operation being performed (enum: "configure", "launch", "destroy")
- `agent_name`: Agent being operated on (string, required)
- `aws_resources_created`: List of AWS resources created during operation (list)
- `local_files_created`: List of local files and directories created (list)
- `operation_stage`: Current stage when error occurred (string)
- `error_timestamp`: When the error occurred (datetime)
- `recovery_actions`: Suggested actions for cleanup (list)

**AWS Resource Tracking**:
- ECR repositories with URIs
- IAM roles with ARNs
- CodeBuild projects with names and ARNs
- S3 buckets and objects for source storage
- Bedrock AgentCore Runtime agents with IDs and ARNs

**Local Resource Tracking**:
- Configuration files and directories
- Build artifact directories
- Temporary files and logs
- Generated Docker files and templates

**Recovery Operations**:
- Automated cleanup of partial resources
- User guidance for manual cleanup when automated cleanup fails
- Resource inventory for troubleshooting and audit purposes
