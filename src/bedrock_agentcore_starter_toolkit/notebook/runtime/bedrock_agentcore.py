"""Bedrock AgentCore Notebook - Jupyter notebook interface for Bedrock AgentCore."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from ...operations.runtime import (
    configure_bedrock_agentcore,
    get_status,
    invoke_bedrock_agentcore,
    launch_bedrock_agentcore,
    validate_agent_name,
)
from ...operations.runtime.models import ConfigureResult, LaunchResult, StatusResult
from ...utils.runtime.entrypoint import parse_entrypoint

# Configure logger for notebook use
log = logging.getLogger(__name__)
if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
    log.setLevel(logging.INFO)


class Runtime:
    """Bedrock AgentCore for Jupyter notebooks - simplified interface for file-based configuration."""

    def __init__(self):
        """Initialize Bedrock AgentCore notebook interface."""
        self._config_path: Optional[Path] = None
        self.name = None

    def configure(
        self,
        entrypoint: str,
        execution_role: str,
        agent_name: Optional[str] = None,
        requirements: Optional[List[str]] = None,
        requirements_file: Optional[str] = None,
        ecr_repository: Optional[str] = None,
        container_runtime: Optional[str] = None,
        auto_create_ecr: bool = True,
        authorizer_configuration: Optional[Dict[str, Any]] = None,
        region: Optional[str] = None,
        protocol: Optional[Literal["HTTP", "MCP"]] = None,
    ) -> ConfigureResult:
        """Configure Bedrock AgentCore from notebook using an entrypoint file.

        Args:
            entrypoint: Path to Python file with optional Bedrock AgentCore name
                (e.g., "handler.py" or "handler.py:bedrock_agentcore")
            execution_role: AWS IAM execution role ARN or name
            agent_name: name of the agent
            requirements: Optional list of requirements to generate requirements.txt
            requirements_file: Optional path to existing requirements file
            ecr_repository: Optional ECR repository URI
            container_runtime: Optional container runtime (docker/podman)
            auto_create_ecr: Whether to auto-create ECR repository
            authorizer_configuration: JWT authorizer configuration dictionary
            region: AWS region for deployment
            protocol: agent server protocol, must be either HTTP or MCP

        Returns:
            ConfigureResult with configuration details
        """
        if protocol and protocol.upper() not in ["HTTP", "MCP"]:
            raise ValueError("protocol must be either HTTP or MCP")

        # Parse entrypoint to get agent name
        file_path, file_name = parse_entrypoint(entrypoint)
        agent_name = agent_name or file_name

        valid, error = validate_agent_name(agent_name)
        if not valid:
            raise ValueError(error)

        # Update our name if not already set
        if not self.name:
            self.name = agent_name

        # Handle requirements
        final_requirements_file = requirements_file

        if requirements and not requirements_file:
            # Create requirements.txt in the same directory as the handler
            handler_dir = Path(file_path).parent
            req_file_path = handler_dir / "requirements.txt"

            all_requirements = []  # "bedrock_agentcore" # Always include bedrock_agentcore
            all_requirements.extend(requirements)

            req_file_path.write_text("\n".join(all_requirements))
            log.info("Generated requirements.txt: %s", req_file_path)

            final_requirements_file = str(req_file_path)

        # Configure using the operations module
        result = configure_bedrock_agentcore(
            agent_name=agent_name,
            entrypoint_path=Path(file_path),
            execution_role=execution_role,
            ecr_repository=ecr_repository,
            container_runtime=container_runtime,
            auto_create_ecr=auto_create_ecr,
            requirements_file=final_requirements_file,
            authorizer_configuration=authorizer_configuration,
            region=region,
            protocol=protocol.upper() if protocol else None,
        )

        self._config_path = result.config_path
        log.info("Bedrock AgentCore configured: %s", self._config_path)
        return result

    def launch(self, local: bool = False, push_ecr: bool = False, env_vars: Optional[Dict] = None) -> LaunchResult:
        """Launch Bedrock AgentCore from notebook.

        Args:
            local: Whether to build for local execution only
            push_ecr: Whether to push to ECR only (no deployment)
            env_vars: environment variables for agent container

        Returns:
            LaunchResult with deployment details
        """
        if not self._config_path:
            raise ValueError("Must configure before launching. Call .configure() first.")

        result = launch_bedrock_agentcore(self._config_path, local=local, push_ecr_only=push_ecr, env_vars=env_vars)

        if result.mode == "cloud":
            log.info("Deployed to cloud: %s", result.agent_arn)
            # Show log information for cloud deployments
            if result.agent_id:
                from ...utils.runtime.logs import get_agent_log_paths, get_aws_tail_commands

                runtime_logs, otel_logs = get_agent_log_paths(result.agent_id)
                follow_cmd, since_cmd = get_aws_tail_commands(runtime_logs)
                log.info("🔍 Agent logs available at:")
                log.info("   %s", runtime_logs)
                log.info("   %s", otel_logs)
                log.info("💡 Tail logs with: %s", follow_cmd)
                log.info("💡 Or view recent logs: %s", since_cmd)
        elif result.mode == "push-ecr":
            log.info("Pushed to ECR: %s", result.ecr_uri)
        else:
            log.info("Built for local: %s", result.tag)

        return result

    def invoke(
        self,
        payload: Dict[str, Any],
        session_id: Optional[str] = None,
        bearer_token: Optional[str] = None,
        local: Optional[bool] = False,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Invoke deployed Bedrock AgentCore endpoint.

        Args:
            payload: Dictionary payload to send
            session_id: Optional session ID for conversation continuity
            bearer_token: Optional bearer token for HTTP authentication
            local: Send request to a running local container
            user_id: User id for authorization flows

        Returns:
            Response from the Bedrock AgentCore endpoint
        """
        if not self._config_path:
            raise ValueError("Must configure and launch first.")

        result = invoke_bedrock_agentcore(
            config_path=self._config_path,
            payload=payload,
            session_id=session_id,
            bearer_token=bearer_token,
            local_mode=local,
            user_id=user_id,
        )
        return result.response

    def status(self) -> StatusResult:
        """Get Bedrock AgentCore status including config and runtime details.

        Returns:
            StatusResult with configuration, agent, and endpoint status
        """
        if not self._config_path:
            raise ValueError("Must configure first. Call .configure() first.")

        result = get_status(self._config_path)
        log.info("Retrieved Bedrock AgentCore status for: %s", self.name or "Bedrock AgentCore")
        return result
