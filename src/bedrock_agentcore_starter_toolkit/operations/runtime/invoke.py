"""Invoke operation - invokes deployed Bedrock AgentCore endpoints."""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from bedrock_agentcore.services.identity import IdentityClient

from ...services.runtime import BedrockAgentCoreClient, generate_session_id
from ...utils.runtime.config import load_config, save_config
from ...utils.runtime.schema import BedrockAgentCoreConfigSchema
from .models import InvokeResult

log = logging.getLogger(__name__)


def invoke_bedrock_agentcore(
    config_path: Path,
    payload: Any,
    agent_name: Optional[str] = None,
    session_id: Optional[str] = None,
    bearer_token: Optional[str] = None,
    user_id: Optional[str] = None,
    local_mode: Optional[bool] = False,
) -> InvokeResult:
    """Invoke deployed Bedrock AgentCore endpoint."""
    # Load project configuration
    project_config = load_config(config_path)
    agent_config = project_config.get_agent_config(agent_name)
    # Log which agent is being invoked
    mode = "locally" if local_mode else "via cloud endpoint"
    log.info("Invoking BedrockAgentCore agent '%s' %s", agent_config.name, mode)

    region = agent_config.aws.region
    if not region:
        raise ValueError("Region not configured.")

    agent_arn = agent_config.bedrock_agentcore.agent_arn

    # Handle session ID
    if not session_id:
        session_id = agent_config.bedrock_agentcore.agent_session_id
        if not session_id:
            session_id = generate_session_id()

    # Save session ID for reuse
    agent_config.bedrock_agentcore.agent_session_id = session_id

    # Update project config and save
    project_config.agents[agent_config.name] = agent_config
    save_config(project_config, config_path)

    # Convert payload to string if needed
    if isinstance(payload, dict):
        payload_str = json.dumps(payload)
    else:
        payload_str = str(payload)

    if local_mode:
        from ...services.runtime import LocalBedrockAgentCoreClient

        identity_client = IdentityClient(region)
        workload_name = _get_workload_name(project_config, config_path, agent_config.name, identity_client)
        workload_access_token = identity_client.get_workload_access_token(
            workload_name=workload_name, user_token=bearer_token, user_id=user_id
        )["workloadAccessToken"]

        # TODO: store and read port config of local running container
        client = LocalBedrockAgentCoreClient("http://0.0.0.0:8080")
        response = client.invoke_endpoint(session_id, payload_str, workload_access_token)

    else:
        if not agent_arn:
            raise ValueError("Bedrock AgentCore not deployed. Run launch first.")

        # Invoke endpoint using appropriate client
        if bearer_token:
            if user_id:
                log.warning("Both bearer token and user id are specified, ignoring user id")

            # Use HTTP client with bearer token
            from ...services.runtime import HttpBedrockAgentCoreClient

            client = HttpBedrockAgentCoreClient(region)
            response = client.invoke_endpoint(
                agent_arn=agent_arn,
                payload=payload_str,
                session_id=session_id,
                bearer_token=bearer_token,
            )
        else:
            # Use existing boto3 client
            bedrock_agentcore_client = BedrockAgentCoreClient(region)
            response = bedrock_agentcore_client.invoke_endpoint(
                agent_arn=agent_arn, payload=payload_str, session_id=session_id, user_id=user_id
            )

    return InvokeResult(
        response=response,
        session_id=session_id,
        agent_arn=agent_arn,
    )


def _get_workload_name(
    project_config: BedrockAgentCoreConfigSchema,
    project_config_path: Path,
    agent_name: str,
    identity_client: IdentityClient,
) -> str:
    agent_config = project_config.get_agent_config(agent_name)
    oauth_config = agent_config.oauth_configuration
    workload_name = None
    if oauth_config:
        workload_name = oauth_config.get("workload_name", None)
    else:
        oauth_config = {}
        agent_config.oauth_configuration = oauth_config

    if not workload_name:
        log.info("Workload not detected, creating...")
        workload_name = identity_client.create_workload_identity()["name"]
        log.info("Created workload %s", workload_name)

    oauth_config["workload_name"] = workload_name
    save_config(project_config, project_config_path)

    return workload_name
