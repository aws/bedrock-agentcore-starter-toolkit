"""Configuration service for loading and managing agent configuration."""

import logging
from pathlib import Path
from typing import Optional

from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config_if_exists
from bedrock_agentcore_starter_toolkit.utils.runtime.schema import (
    BedrockAgentCoreConfigSchema,
)

logger = logging.getLogger(__name__)


class ConfigService:
    """Service for loading and managing agent configuration from project_config.yaml."""

    def __init__(
        self, config_path: Optional[Path] = None, agent_name: Optional[str] = None
    ):
        """Initialize ConfigService.

        Args:
            config_path: Path to project_config.yaml. If None, searches in current directory.
            agent_name: Name of the agent to use. If None, uses default agent.
        """
        self.config_path = config_path or Path.cwd() / "project_config.yaml"
        self.agent_name = agent_name
        self._config: Optional[BedrockAgentCoreConfigSchema] = None
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        try:
            self._config = load_config_if_exists(self.config_path)
            if self._config:
                logger.info(f"Loaded configuration from {self.config_path}")
            else:
                logger.warning(f"Configuration file not found at {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            self._config = None

    def get_config(self) -> Optional[BedrockAgentCoreConfigSchema]:
        """Get the loaded configuration.

        Returns:
            BedrockAgentCoreConfigSchema or None if not loaded
        """
        return self._config

    def get_agent_config(self, agent_name: Optional[str] = None):
        """Get agent configuration by name or default agent.

        Args:
            agent_name: Name of the agent. If None, uses instance agent_name or default agent.

        Returns:
            Agent configuration or None if not found
        """
        if not self._config:
            return None

        try:
            # Use provided agent_name, or fall back to instance agent_name
            name_to_use = agent_name or self.agent_name
            return self._config.get_agent_config(name_to_use)
        except Exception as e:
            logger.error(f"Failed to get agent config: {e}")
            return None

    def get_agent_name(self, agent_name: Optional[str] = None) -> Optional[str]:
        """Get agent name (uses default if not specified).

        Args:
            agent_name: Name of the agent. If None, uses default agent.

        Returns:
            Agent name or None if not found
        """
        agent_config = self.get_agent_config(agent_name)
        return agent_config.name if agent_config else None

    def get_agent_arn(self, agent_name: Optional[str] = None) -> Optional[str]:
        """Get agent ARN.

        Args:
            agent_name: Name of the agent. If None, uses default agent.

        Returns:
            Agent ARN or None if not found
        """
        agent_config = self.get_agent_config(agent_name)
        if not agent_config:
            return None
        return (
            agent_config.bedrock_agentcore.agent_arn
            if agent_config.bedrock_agentcore
            else None
        )

    def get_region(self, agent_name: Optional[str] = None) -> Optional[str]:
        """Get AWS region.

        Args:
            agent_name: Name of the agent. If None, uses default agent.

        Returns:
            AWS region or None if not found
        """
        agent_config = self.get_agent_config(agent_name)
        if not agent_config:
            return None
        return agent_config.aws.region if agent_config.aws else None

    def get_memory_id(self, agent_name: Optional[str] = None) -> Optional[str]:
        """Get memory ID if configured.

        Args:
            agent_name: Name of the agent. If None, uses default agent.

        Returns:
            Memory ID or None if not configured
        """
        agent_config = self.get_agent_config(agent_name)
        if not agent_config:
            return None
        return agent_config.memory.memory_id if agent_config.memory else None

    def has_oauth_config(self, agent_name: Optional[str] = None) -> bool:
        """Check if OAuth configuration exists.

        Args:
            agent_name: Name of the agent. If None, uses default agent.

        Returns:
            True if OAuth is configured, False otherwise
        """
        agent_config = self.get_agent_config(agent_name)
        if not agent_config:
            return False
        return bool(agent_config.authorizer_configuration)

    def is_configured(self) -> bool:
        """Check if configuration is loaded.

        Returns:
            True if configuration is loaded, False otherwise
        """
        return self._config is not None
