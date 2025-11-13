"""Unit tests for YAML output generation in create."""

import yaml

from bedrock_agentcore_starter_toolkit.create.util.create_with_iac_yaml import (
    write_minimal_create_with_iac_project_yaml,
)


class TestYAMLOutput:
    """Test suite for YAML configuration file generation."""

    def test_yaml_file_created(self, sample_project_context):
        """Test that YAML file is created in the output directory."""
        # Ensure output directory exists
        sample_project_context.output_dir.mkdir(parents=True, exist_ok=True)

        # Write YAML file
        yaml_path = write_minimal_create_with_iac_project_yaml(sample_project_context)

        # Verify file was created
        assert yaml_path.exists()
        assert yaml_path.name == ".bedrock_agentcore.yaml"
        assert yaml_path.parent == sample_project_context.output_dir

    def test_yaml_includes_agent_name(self, sample_project_context):
        """Test that YAML includes the agent name from ProjectContext."""
        # Ensure output directory exists
        sample_project_context.output_dir.mkdir(parents=True, exist_ok=True)

        # Write YAML file
        yaml_path = write_minimal_create_with_iac_project_yaml(sample_project_context)

        # Read and parse YAML
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        # Verify agent name is included
        assert "agents" in data
        assert sample_project_context.agent_name in data["agents"]
        assert data["agents"][sample_project_context.agent_name]["name"] == sample_project_context.agent_name
        assert data["default_agent"] == sample_project_context.agent_name

    def test_yaml_includes_entrypoint(self, sample_project_context):
        """Test that YAML includes the entrypoint path from ProjectContext."""
        # Ensure output directory exists
        sample_project_context.output_dir.mkdir(parents=True, exist_ok=True)

        # Write YAML file
        yaml_path = write_minimal_create_with_iac_project_yaml(sample_project_context)

        # Read and parse YAML
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        # Verify entrypoint is included (should be src_dir as string)
        agent_config = data["agents"][sample_project_context.agent_name]
        assert "entrypoint" in agent_config
        assert agent_config["entrypoint"] == str(sample_project_context.src_dir)

    def test_yaml_includes_deployment_type(self, sample_project_context):
        """Test that YAML includes the deployment type from ProjectContext."""
        # Ensure output directory exists
        sample_project_context.output_dir.mkdir(parents=True, exist_ok=True)

        # Write YAML file
        yaml_path = write_minimal_create_with_iac_project_yaml(sample_project_context)

        # Read and parse YAML
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        # Verify deployment type is included
        agent_config = data["agents"][sample_project_context.agent_name]
        assert "deployment_type" in agent_config
        assert agent_config["deployment_type"] == sample_project_context.deployment_type

    def test_yaml_sets_create_flag(self, sample_project_context):
        """Test that YAML sets is_agentcore_create_project flag to True."""
        # Ensure output directory exists
        sample_project_context.output_dir.mkdir(parents=True, exist_ok=True)

        # Write YAML file
        yaml_path = write_minimal_create_with_iac_project_yaml(sample_project_context)

        # Read and parse YAML
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        # Verify create flag is set to True
        assert "is_agentcore_create_project" in data
        assert data["is_agentcore_create_project"] is True

    def test_yaml_structure_valid(self, sample_project_context):
        """Test that YAML structure is valid and contains all required sections."""
        # Ensure output directory exists
        sample_project_context.output_dir.mkdir(parents=True, exist_ok=True)

        # Write YAML file
        yaml_path = write_minimal_create_with_iac_project_yaml(sample_project_context)

        # Read and parse YAML
        with open(yaml_path) as f:
            data = yaml.safe_load(f)

        # Verify top-level structure
        assert isinstance(data, dict)
        assert "default_agent" in data
        assert "is_agentcore_create_project" in data
        assert "agents" in data

        # Verify agent structure
        agent_name = sample_project_context.agent_name
        assert agent_name in data["agents"]
        agent_config = data["agents"][agent_name]

        assert "name" in agent_config
        assert "entrypoint" in agent_config
        assert "deployment_type" in agent_config
        assert "aws" in agent_config
        assert "bedrock_agentcore" in agent_config

        # Verify aws section
        assert isinstance(agent_config["aws"], dict)
        assert "region" in agent_config["aws"]

        # Verify bedrock_agentcore section
        assert isinstance(agent_config["bedrock_agentcore"], dict)
        assert "agent_id" in agent_config["bedrock_agentcore"]
        assert "agent_arn" in agent_config["bedrock_agentcore"]
        assert "agent_session_id" in agent_config["bedrock_agentcore"]
