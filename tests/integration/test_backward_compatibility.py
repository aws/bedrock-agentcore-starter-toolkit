"""Integration tests for backward compatibility validation.

This module tests that the enhanced configuration management maintains
complete backward compatibility with existing .bedrock_agentcore.yaml files.
"""

import tempfile
from pathlib import Path

import yaml

from bedrock_agentcore_starter_toolkit.utils.runtime.backward_compat import (
    generate_compatibility_report,
    simulate_legacy_load,
    validate_legacy_config_compatibility,
)
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    BedrockAgentCoreAgentSchema,
    BedrockAgentCoreConfigSchema,
)


class TestBackwardCompatibilityIntegration:
    """Integration tests for backward compatibility validation."""

    def test_existing_config_loads_unchanged(self):
        """Test that existing configurations load without modification."""

        # Sample existing configuration
        existing_config = {
            "default_agent": "my-agent",
            "agents": {
                "my-agent": {
                    "name": "my-agent",
                    "entrypoint": "agent.py",
                    "platform": "linux/arm64",
                    "container_runtime": "none",
                    "aws": {
                        "execution_role": "arn:aws:iam::123456789012:role/MyRole",
                        "execution_role_auto_create": False,
                        "account": "123456789012",
                        "region": "us-west-2",
                        "ecr_repository": "123456789012.dkr.ecr.us-west-2.amazonaws.com/my-agent",
                        "ecr_auto_create": False,
                        "network_configuration": {"network_mode": "PUBLIC"},
                        "protocol_configuration": {"server_protocol": "HTTP"},
                        "observability": {"enabled": True},
                    },
                    "bedrock_agentcore": {
                        "agent_id": "my-agent-xyz123",
                        "agent_arn": "arn:aws:bedrock-agentcore:us-west-2:123456789012:runtime/my-agent-xyz123",
                        "agent_session_id": None,
                    },
                    "codebuild": {
                        "project_name": "bedrock-agentcore-my-agent-builder",
                        "execution_role": "arn:aws:iam::123456789012:role/CodeBuildRole",
                        "source_bucket": "bedrock-agentcore-codebuild-sources-123456789012-us-west-2",
                    },
                }
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / ".bedrock_agentcore.yaml"

            # Write existing config
            with open(config_path, "w") as f:
                yaml.safe_dump(existing_config, f)

            # Should load with enhanced schema without issues
            config_schema = BedrockAgentCoreConfigSchema.model_validate(existing_config)

            # Verify all fields are preserved
            assert config_schema.default_agent == "my-agent"
            assert "my-agent" in config_schema.agents

            agent_config = config_schema.agents["my-agent"]
            assert agent_config.name == "my-agent"
            assert agent_config.entrypoint == "agent.py"
            assert agent_config.source_path is None  # New field defaults to None
            assert agent_config.build_artifacts is None  # New field defaults to None

            # Backward compatibility validation should pass
            assert validate_legacy_config_compatibility(existing_config) is True

    def test_legacy_load_simulation_passes(self):
        """Test that enhanced config would work in legacy system."""

        enhanced_config = {
            "default_agent": "enhanced-agent",
            "agents": {
                "enhanced-agent": {
                    "name": "enhanced-agent",
                    "entrypoint": "agent.py",
                    "source_path": "/path/to/source",  # New field
                    "build_artifacts": {  # New field
                        "base_directory": ".packages/enhanced-agent",
                        "organized": True,
                    },
                    "aws": {"region": "us-west-2", "account": "123456789012"},
                }
            },
        }

        # Legacy simulation should strip new fields and still work
        assert simulate_legacy_load(enhanced_config) is True

    def test_config_with_missing_new_fields_works(self):
        """Test that configs without new fields continue to work."""

        minimal_config = {"agents": {"minimal-agent": {"name": "minimal-agent", "entrypoint": "agent.py"}}}

        # Should load successfully
        config_schema = BedrockAgentCoreConfigSchema.model_validate(minimal_config)
        agent_config = config_schema.agents["minimal-agent"]

        # New fields should default to None
        assert agent_config.source_path is None
        assert agent_config.build_artifacts is None

        # Validation should pass for local deployment
        errors = agent_config.validate(for_local=True)
        assert len(errors) == 0

    def test_config_loading_preserves_all_existing_fields(self):
        """Test that enhanced loading preserves all existing fields."""

        complex_existing_config = {
            "default_agent": "complex-agent",
            "agents": {
                "complex-agent": {
                    "name": "complex-agent",
                    "entrypoint": "complex_agent.py",
                    "platform": "linux/amd64",
                    "container_runtime": "docker",
                    "aws": {
                        "execution_role": "arn:aws:iam::123456789012:role/ComplexRole",
                        "execution_role_auto_create": True,
                        "account": "123456789012",
                        "region": "eu-west-1",
                        "ecr_repository": None,
                        "ecr_auto_create": True,
                        "network_configuration": {"network_mode": "VPC"},
                        "protocol_configuration": {"server_protocol": "HTTPS"},
                        "observability": {"enabled": False},
                    },
                    "bedrock_agentcore": {"agent_id": None, "agent_arn": None, "agent_session_id": None},
                    "codebuild": {"project_name": None, "execution_role": None, "source_bucket": None},
                    "memory": {
                        "mode": "STM_AND_LTM",
                        "memory_id": "mem-123",
                        "memory_arn": "arn:aws:bedrock-agentcore:eu-west-1:123456789012:memory/mem-123",
                        "memory_name": "complex-memory",
                        "event_expiry_days": 90,
                        "first_invoke_memory_check_done": True,
                    },
                    "authorizer_configuration": {"type": "JWT", "issuer": "https://issuer.com"},
                    "request_header_configuration": {"required_headers": ["Authorization"]},
                    "oauth_configuration": {"client_id": "oauth-client-123"},
                }
            },
        }

        # Load with enhanced schema
        config_schema = BedrockAgentCoreConfigSchema.model_validate(complex_existing_config)
        agent_config = config_schema.agents["complex-agent"]

        # Verify all existing fields are preserved exactly
        assert agent_config.platform == "linux/amd64"
        assert agent_config.container_runtime == "docker"
        assert agent_config.aws.region == "eu-west-1"
        assert agent_config.aws.ecr_auto_create is True
        assert agent_config.memory.mode == "STM_AND_LTM"
        assert agent_config.memory.event_expiry_days == 90
        assert agent_config.authorizer_configuration["type"] == "JWT"

        # New fields should be None
        assert agent_config.source_path is None
        assert agent_config.build_artifacts is None

    def test_compatibility_report_generation(self):
        """Test comprehensive compatibility report generation."""

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / ".bedrock_agentcore.yaml"

            # Create a config with potential compatibility issues
            test_config = {
                "default_agent": "test-agent",
                "agents": {
                    "test-agent": {
                        "name": "test-agent",
                        "entrypoint": "agent.py",
                        "aws": {"region": "us-west-2", "account": "123456789012"},
                    }
                },
            }

            with open(config_path, "w") as f:
                yaml.safe_dump(test_config, f)

            # Generate compatibility report
            report = generate_compatibility_report(config_path)

            # Report should have required fields
            assert "config_path" in report
            assert "compatible" in report
            assert "errors" in report
            assert "warnings" in report
            assert "legacy_simulation" in report
            assert "summary" in report

            # Report should indicate compatibility status
            assert isinstance(report["compatible"], bool)
            assert isinstance(report["errors"], list)
            assert isinstance(report["warnings"], list)

    def test_enhanced_config_backward_serialization(self):
        """Test that enhanced configs can be serialized back to YAML."""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "source"
            source_dir.mkdir()
            (source_dir / "agent.py").write_text("# Agent code")

            # Create enhanced config
            enhanced_config = BedrockAgentCoreConfigSchema(
                default_agent="enhanced-agent",
                agents={
                    "enhanced-agent": BedrockAgentCoreAgentSchema(
                        name="enhanced-agent", entrypoint="agent.py", source_path=str(source_dir)
                    )
                },
            )

            # Serialize to dict
            config_dict = enhanced_config.model_dump()

            # Should be serializable to YAML
            yaml_str = yaml.safe_dump(config_dict)
            assert isinstance(yaml_str, str)
            assert "enhanced-agent" in yaml_str

            # Should be loadable by legacy systems (new fields ignored)
            loaded_config = yaml.safe_load(yaml_str)
            assert loaded_config["default_agent"] == "enhanced-agent"
            assert "source_path" in loaded_config["agents"]["enhanced-agent"]

    def test_mixed_legacy_and_enhanced_agents(self):
        """Test configuration with both legacy and enhanced agents."""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_dir = temp_path / "enhanced_source"
            source_dir.mkdir()
            (source_dir / "enhanced.py").write_text("# Enhanced agent code")

            mixed_config = {
                "default_agent": "enhanced-agent",
                "agents": {
                    "legacy-agent": {
                        "name": "legacy-agent",
                        "entrypoint": "legacy.py",
                        "aws": {"region": "us-west-2", "account": "123456789012"},
                    },
                    "enhanced-agent": {
                        "name": "enhanced-agent",
                        "entrypoint": "enhanced.py",
                        "source_path": str(source_dir),
                        "aws": {"region": "us-west-2", "account": "123456789012"},
                    },
                },
            }

            # Should load successfully - run inside the context while temp dir exists
            config_schema = BedrockAgentCoreConfigSchema.model_validate(mixed_config)

            # Legacy agent should have new fields as None
            legacy_agent = config_schema.agents["legacy-agent"]
            assert legacy_agent.source_path is None
            assert legacy_agent.build_artifacts is None

            # Enhanced agent should have new fields populated
            enhanced_agent = config_schema.agents["enhanced-agent"]
            assert enhanced_agent.source_path == str(source_dir.resolve())
            assert enhanced_agent.build_artifacts is None  # Not yet populated

            # Both should validate for local deployment
            assert len(legacy_agent.validate(for_local=True)) == 0
            assert len(enhanced_agent.validate(for_local=True)) == 0

    def test_config_migration_not_required(self):
        """Test that no configuration migration is required."""

        # This test verifies the core requirement: zero breaking changes
        existing_configs = [
            # Minimal config
            {"agents": {"minimal": {"name": "minimal", "entrypoint": "agent.py"}}},
            # Complex config with all optional fields
            {
                "default_agent": "complex",
                "agents": {
                    "complex": {
                        "name": "complex",
                        "entrypoint": "agent.py",
                        "platform": "linux/arm64",
                        "container_runtime": "none",
                        "aws": {
                            "region": "us-west-2",
                            "account": "123456789012",
                            "execution_role": "arn:aws:iam::123456789012:role/Role",
                        },
                        "memory": {"mode": "STM_ONLY"},
                        "authorizer_configuration": None,
                        "request_header_configuration": None,
                        "oauth_configuration": None,
                    }
                },
            },
        ]

        for config_data in existing_configs:
            # Should load without any migration
            config_schema = BedrockAgentCoreConfigSchema.model_validate(config_data)

            # Should validate successfully
            assert isinstance(config_schema, BedrockAgentCoreConfigSchema)

            # All agents should have new fields defaulting to None
            for agent_name, agent_config in config_schema.agents.items():
                assert agent_config.source_path is None
                assert agent_config.build_artifacts is None

            # Should pass backward compatibility validation
            assert validate_legacy_config_compatibility(config_data) is True
