# Data Model: Enhanced Configuration Management with Backward Compatibility

## Enhanced Agent Configuration Entity

**Purpose**: Extend existing agent configuration with optional source path tracking and build artifact information

**Extended Attributes** (all optional for backward compatibility):
- `source_path`: Directory containing agent source code (string, optional)
- `build_artifacts`: Build artifact organization information (nested object, optional)

**Existing Attributes** (unchanged):
- `name`: Unique identifier for the agent (string, required)
- `entrypoint`: Path to agent's main file (string, required)
- `platform`: Target deployment platform (string, default: "linux/arm64")
- `container_runtime`: Runtime environment (enum: "none", "docker")
- `aws_config`: AWS-specific deployment configuration (nested object)
- `bedrock_agentcore_config`: AgentCore Runtime deployment state (nested object)
- `codebuild_config`: Build pipeline configuration (nested object)
- `memory_config`: Optional memory service configuration (nested object)

**Validation Rules** (backward compatible):
- All existing validation rules remain unchanged
- Source path validation only occurs if source_path is provided
- Build artifact information is auto-populated during launch, not user-provided
- Configuration loading gracefully handles missing optional fields

**State Transitions** (unchanged):
- CONFIGURED → BUILDING → BUILT → DEPLOYED → READY
- READY → UPDATING → READY (for updates)
- READY → DESTROYING → DESTROYED (for cleanup)

## Build Artifact Organization Entity

**Purpose**: Track build artifact locations for each agent in predictable, organized structure

**Attributes**:
- `agent_name`: Associated agent identifier (string, required)
- `base_directory`: Root directory for agent's build artifacts (string, auto-generated)
- `source_copy_path`: Path to copied source code (string, auto-generated)
- `dockerfile_path`: Path to generated Dockerfile (string, auto-generated)
- `build_timestamp`: When artifacts were created (datetime, auto-populated)

**Organization Pattern**:
```
.packages/
├── {agent-name}/
│   ├── src/                    # Copied source code
│   ├── Dockerfile              # Generated Dockerfile
│   └── build_metadata.json     # Build information
```

**Lifecycle**:
- Created automatically during `agentcore launch`
- Organized by agent name for clear separation
- Cleaned up automatically during `agentcore destroy`
- Maintained separately for each agent to prevent conflicts

**Relationships**:
- Belongs to exactly one Enhanced Agent Configuration
- Contains references to copied source files and generated deployment files
- Independent from other agents' build artifacts

## Source Path Tracking Entity

**Purpose**: Simple mechanism to track and validate source code locations for each agent

**Attributes**:
- `agent_name`: Associated agent identifier (string, required)
- `source_path`: Absolute path to source code directory (string, required)
- `entrypoint_resolved`: Resolved path to entrypoint file (string, derived)
- `last_validated`: When source path was last validated (datetime, auto-updated)

**Validation Rules**:
- Source path must exist and be accessible
- Entrypoint file must exist within source path
- Path resolution follows existing entrypoint validation patterns
- Validation occurs before launch operations

**Integration**:
- Integrates with existing entrypoint validation in `utils/runtime/entrypoint.py`
- Uses existing path resolution utilities
- Maintains compatibility with existing validation workflows

## Configuration Schema Extensions

**Backward Compatibility Design**:
- All new fields are optional with sensible defaults
- Existing configurations load without modification
- Schema validation gracefully handles missing fields
- Configuration saving preserves all existing fields

**Migration Strategy**:
- No migration required - existing configs work as-is
- New fields populated on first use of enhanced features
- Users can gradually adopt new functionality per agent
- Legacy behavior maintained for configurations without new fields

**Pydantic Model Extensions**:
```python
# New optional fields added to existing BedrockAgentCoreAgentSchema
source_path: Optional[str] = None
build_artifacts: Optional[BuildArtifactInfo] = None

class BuildArtifactInfo(BaseModel):
    base_directory: Optional[str] = None
    source_copy_path: Optional[str] = None
    dockerfile_path: Optional[str] = None
    build_timestamp: Optional[datetime] = None
```

## Relationships and Dependencies

**Enhanced Agent Configuration**:
- Extends existing configuration without breaking changes
- Maintains all existing relationships (AWS config, CodeBuild, etc.)
- Adds optional source tracking and build artifact references

**Build Artifact Organization**:
- One-to-one relationship with Enhanced Agent Configuration
- Independent lifecycle from AWS resources
- Local file system organization only

**Source Path Tracking**:
- Integrated into existing configuration validation workflow
- Uses existing path resolution and validation utilities
- Compatible with existing entrypoint handling patterns

## Data Persistence

**Configuration Storage** (unchanged pattern):
- YAML-based `.bedrock_agentcore.yaml` file
- Pydantic model serialization/deserialization
- Immediate persistence after configuration changes
- Backward compatible loading with graceful defaults

**Build Artifact Tracking**:
- Local file system organization
- No persistent storage required beyond file organization
- Build metadata stored in JSON files within artifact directories
- Cleaned up automatically with artifact cleanup

**Source Path References**:
- Stored as part of agent configuration in YAML
- Validated on load and before operations
- No separate storage mechanism required
- Integrates with existing configuration persistence patterns
