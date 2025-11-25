"""Utilities for writing create project YAML configuration files."""

from pathlib import Path

import yaml

from ...utils.runtime.config import save_config
from ...utils.runtime.schema import AWSConfig, BedrockAgentCoreAgentSchema, BedrockAgentCoreConfigSchema
from ..constants import MemoryConfig
from ..types import CreateMemoryType, ProjectContext

CONFIG_YAML_NAME = ".bedrock_agentcore.yaml"


def write_minimal_create_with_iac_project_yaml(ctx: ProjectContext) -> Path:
    """Create and write a minimal create project YAML configuration file from the project context."""
    file_path = ctx.output_dir / CONFIG_YAML_NAME
    agent_name = ctx.agent_name

    data = {
        "default_agent": agent_name,
        "is_agentcore_create_with_iac": True,
        "agents": {
            agent_name: {
                "name": agent_name,
                "entrypoint": str(ctx.entrypoint_path),
                "deployment_type": ctx.deployment_type,
                "source_path": str(ctx.src_dir),
                "aws": {"account": None, "region": None},
                "bedrock_agentcore": {
                    "agent_id": None,
                    "agent_arn": None,
                    "agent_session_id": None,
                },
                "is_generated_by_agentcore_create": True,
            }
        },
    }

    with file_path.open("w") as f:
        yaml.safe_dump(data, f, sort_keys=False)

    return file_path


def write_minimal_create_runtime_yaml(ctx: ProjectContext, memory: CreateMemoryType | None) -> Path:
    """Create the most simple .bedrock_agentcore.yaml for runtime projects."""
    agent_schema = BedrockAgentCoreAgentSchema(
        name=ctx.agent_name,
        entrypoint=str(ctx.entrypoint_path),
        deployment_type=ctx.deployment_type,
        runtime_type="PYTHON_3_10",  # todo need to decide default here
        source_path=str(ctx.src_dir),
        aws=AWSConfig(execution_role_auto_create=True, s3_auto_create=True, region=None, account=None),
        api_key_env_var_name=ctx.api_key_env_var_name,
        is_generated_by_agentcore_create=True,
    )

    # Only add memory config if it's enabled
    if ctx.memory_enabled:
        memory_config = MemoryConfig()
        memory_config.mode = memory or MemoryConfig.NONE
        memory_config.memory_name = ctx.memory_name
        memory_config.event_expiry_days = ctx.memory_event_expiry_days or 30
        agent_schema.memory = memory_config

    schema = BedrockAgentCoreConfigSchema(default_agent=ctx.agent_name, agents={ctx.agent_name: agent_schema})
    config_path = ctx.output_dir / CONFIG_YAML_NAME
    save_config(schema, config_path)
    return config_path
