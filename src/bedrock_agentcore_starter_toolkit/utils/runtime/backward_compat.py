"""Backward compatibility validation utilities for enhanced configuration management.

This module provides utilities to ensure that existing .bedrock_agentcore.yaml
configurations continue to work unchanged when new optional fields are added.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)


def validate_legacy_config_compatibility(config_data: dict[str, Any]) -> bool:
    """Validate that a configuration maintains backward compatibility.

    Args:
        config_data: Configuration dictionary loaded from YAML

    Returns:
        True if configuration is backward compatible, False otherwise
    """
    try:
        # Check for required legacy fields
        required_fields = ["agents"]
        for field in required_fields:
            if field not in config_data:
                logger.warning("Legacy config missing required field: %s", field)
                return False

        # Validate each agent configuration has required fields
        agents = config_data.get("agents", {})
        for agent_name, agent_config in agents.items():
            if not validate_legacy_agent_config(agent_config, agent_name):
                return False

        logger.debug("Legacy configuration validation passed")
        return True

    except Exception as e:
        logger.error("Error validating legacy configuration: %s", e)
        return False


def validate_legacy_agent_config(agent_config: dict[str, Any], agent_name: str) -> bool:
    """Validate that an individual agent configuration is backward compatible.

    Args:
        agent_config: Agent configuration dictionary
        agent_name: Name of the agent for logging

    Returns:
        True if agent config is backward compatible, False otherwise
    """
    required_fields = ["name", "entrypoint"]

    for field in required_fields:
        if field not in agent_config:
            logger.warning("Agent '%s' missing required field: %s", agent_name, field)
            return False

    # Validate that existing fields have expected types
    if not isinstance(agent_config.get("name"), str):
        logger.warning("Agent '%s' has invalid name type", agent_name)
        return False

    if not isinstance(agent_config.get("entrypoint"), str):
        logger.warning("Agent '%s' has invalid entrypoint type", agent_name)
        return False

    return True


def check_new_fields_are_optional(config_data: dict[str, Any]) -> list[str]:
    """Check that any new fields in the configuration are properly optional.

    Args:
        config_data: Configuration dictionary loaded from YAML

    Returns:
        List of warnings about new fields that might break compatibility
    """
    warnings = []

    # Check for new fields at the top level
    expected_fields = {"default_agent", "agents"}
    extra_fields = set(config_data.keys()) - expected_fields

    for field in extra_fields:
        if config_data[field] is not None:
            warnings.append(f"New top-level field '{field}' has non-null value")

    # Check for new fields in agent configurations
    agents = config_data.get("agents", {})
    for agent_name, agent_config in agents.items():
        agent_warnings = check_new_agent_fields(agent_config, agent_name)
        warnings.extend(agent_warnings)

    return warnings


def check_new_agent_fields(agent_config: dict[str, Any], agent_name: str) -> list[str]:
    """Check that new agent-level fields are properly optional.

    Args:
        agent_config: Agent configuration dictionary
        agent_name: Name of the agent for logging

    Returns:
        List of warnings about new agent fields
    """
    warnings = []

    # Expected legacy fields
    expected_fields = {
        "name",
        "entrypoint",
        "platform",
        "container_runtime",
        "aws",
        "bedrock_agentcore",
        "codebuild",
        "memory",
        "authorizer_configuration",
        "request_header_configuration",
        "oauth_configuration",
    }

    # Check for new fields
    extra_fields = set(agent_config.keys()) - expected_fields
    new_fields = {"source_path", "build_artifacts"}  # Known new fields

    for field in extra_fields:
        if field in new_fields:
            # These are expected new fields - check they're optional
            if agent_config[field] is not None:
                warnings.append(f"Agent '{agent_name}' new field '{field}' should be optional")
        else:
            # Unexpected new field
            warnings.append(f"Agent '{agent_name}' has unexpected new field: '{field}'")

    return warnings


def load_and_validate_legacy_config(config_path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Load a configuration file and validate its backward compatibility.

    Args:
        config_path: Path to the configuration file

    Returns:
        Tuple of (config_data, validation_errors)
        config_data is None if file cannot be loaded
    """
    try:
        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        if not config_data:
            return None, ["Configuration file is empty"]

        errors = []

        # Check basic backward compatibility
        if not validate_legacy_config_compatibility(config_data):
            errors.append("Configuration fails backward compatibility validation")

        # Check for optional field issues
        warnings = check_new_fields_are_optional(config_data)
        errors.extend(warnings)

        return config_data, errors

    except FileNotFoundError:
        return None, [f"Configuration file not found: {config_path}"]
    except yaml.YAMLError as e:
        return None, [f"YAML parsing error: {e}"]
    except Exception as e:
        return None, [f"Unexpected error loading configuration: {e}"]


def simulate_legacy_load(config_data: dict[str, Any]) -> bool:
    """Simulate loading configuration data as if it were a legacy system.

    This function tests that the configuration would work in a system that
    doesn't know about the new optional fields.

    Args:
        config_data: Configuration dictionary

    Returns:
        True if legacy load simulation succeeds, False otherwise
    """
    try:
        # Create a copy without new fields
        legacy_config = {}

        # Top-level fields
        if "default_agent" in config_data:
            legacy_config["default_agent"] = config_data["default_agent"]

        if "agents" in config_data:
            legacy_config["agents"] = {}
            for agent_name, agent_config in config_data["agents"].items():
                legacy_agent = {}

                # Copy only legacy fields
                legacy_fields = [
                    "name",
                    "entrypoint",
                    "platform",
                    "container_runtime",
                    "aws",
                    "bedrock_agentcore",
                    "codebuild",
                    "memory",
                    "authorizer_configuration",
                    "request_header_configuration",
                    "oauth_configuration",
                ]

                for field in legacy_fields:
                    if field in agent_config:
                        legacy_agent[field] = agent_config[field]

                legacy_config["agents"][agent_name] = legacy_agent

        # Validate the legacy configuration works
        return validate_legacy_config_compatibility(legacy_config)

    except Exception as e:
        logger.error("Error in legacy load simulation: %s", e)
        return False


def generate_compatibility_report(config_path: Path) -> dict[str, Any]:
    """Generate a comprehensive backward compatibility report.

    Args:
        config_path: Path to the configuration file

    Returns:
        Dictionary containing compatibility analysis results
    """
    report = {
        "config_path": str(config_path),
        "compatible": False,
        "errors": [],
        "warnings": [],
        "legacy_simulation": False,
        "summary": "",
    }

    try:
        config_data, errors = load_and_validate_legacy_config(config_path)

        if config_data is None:
            report["errors"] = errors
            report["summary"] = "Configuration file could not be loaded"
            return report

        report["errors"] = [e for e in errors if "warning" not in e.lower()]
        report["warnings"] = [e for e in errors if "warning" in e.lower()]

        # Test legacy simulation
        report["legacy_simulation"] = simulate_legacy_load(config_data)

        # Determine overall compatibility
        report["compatible"] = len(report["errors"]) == 0 and report["legacy_simulation"]

        # Generate summary
        if report["compatible"]:
            report["summary"] = "Configuration is fully backward compatible"
        else:
            issues = len(report["errors"])
            report["summary"] = f"Configuration has {issues} compatibility issues"

        return report

    except Exception as e:
        report["errors"] = [f"Error generating compatibility report: {e}"]
        report["summary"] = "Compatibility analysis failed"
        return report
