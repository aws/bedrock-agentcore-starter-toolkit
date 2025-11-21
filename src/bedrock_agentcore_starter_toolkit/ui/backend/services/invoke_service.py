"""Invoke service for calling AgentCore agents."""

import logging
from pathlib import Path
from typing import Optional

from bedrock_agentcore_starter_toolkit.operations.runtime.invoke import (
    invoke_bedrock_agentcore,
)
from bedrock_agentcore_starter_toolkit.services.runtime import generate_session_id

logger = logging.getLogger(__name__)


class InvokeService:
    """Service for invoking AgentCore agents."""

    def __init__(
        self,
        config_path: Path,
        agent_name: Optional[str] = None,
        local_mode: bool = False,
    ):
        """Initialize InvokeService.

        Args:
            config_path: Path to project_config.yaml
            agent_name: Name of the agent to use. If None, uses default agent.
            local_mode: Whether to use local mode (container at localhost:8000)
        """
        self.config_path = config_path
        self.agent_name = agent_name
        self.local_mode = local_mode
        self.current_session_id: Optional[str] = None

    def invoke(
        self,
        message: str,
        session_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        bearer_token: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Invoke the agent with a message.

        Args:
            message: User message to send to agent
            session_id: Session ID for conversation context. If None, generates new one.
            agent_name: Name of agent to invoke. If None, uses instance agent_name or default.
            bearer_token: Bearer token for OAuth authentication (remote mode only)
            user_id: User ID for IAM authentication (remote mode only)

        Returns:
            Dict with response, session_id, and agent_arn

        Raises:
            Exception: If invocation fails
        """
        # Use provided session ID or generate new one
        if not session_id:
            session_id = self.current_session_id or generate_session_id()
            self.current_session_id = session_id

        logger.info("Invoking agent with session ID: %s", session_id)

        # Use provided agent_name, or fall back to instance agent_name
        name_to_use = agent_name or self.agent_name

        try:
            result = invoke_bedrock_agentcore(
                config_path=self.config_path,
                payload=message,
                agent_name=name_to_use,
                session_id=session_id,
                bearer_token=bearer_token,
                user_id=user_id,
                local_mode=self.local_mode,
            )

            # Update current session ID
            self.current_session_id = result.session_id

            return {
                "response": result.response,
                "session_id": result.session_id,
                "agent_arn": result.agent_arn,
            }

        except Exception as e:
            logger.error("Failed to invoke agent: %s", e)
            raise

    def generate_new_session_id(self) -> str:
        """Generate a new session ID.

        Returns:
            New session ID
        """
        self.current_session_id = generate_session_id()
        logger.info("Generated new session ID: %s", self.current_session_id)
        return self.current_session_id

    def get_current_session_id(self) -> Optional[str]:
        """Get the current session ID.

        Returns:
            Current session ID or None
        """
        return self.current_session_id
