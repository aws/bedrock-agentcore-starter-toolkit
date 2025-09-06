"""BedrockAgentCore service client for agent management."""

import json
import logging
import time
import urllib.parse
import uuid
from typing import Any, Dict, Optional

import boto3
import requests
from botocore.config import Config
from botocore.exceptions import ClientError
from rich.console import Console

from ..utils.endpoints import get_control_plane_endpoint, get_data_plane_endpoint

logger = logging.getLogger(__name__)
console = Console()


def generate_session_id() -> str:
    """Generate session ID."""
    return str(uuid.uuid4())


def _handle_http_response(response) -> dict:
    response.raise_for_status()
    if "text/event-stream" in response.headers.get("content-type", ""):
        return _handle_streaming_response(response)
    else:
        # Check if response has content
        if not response.content:
            raise ValueError("Empty response from agent endpoint")

        return {"response": response.text}


def _handle_aws_response(response) -> dict:
    if "text/event-stream" in response.get("contentType", ""):
        return _handle_streaming_response(response["response"])
    else:
        try:
            events = []
            for event in response.get("response", []):
                events.append(event)
        except Exception as e:
            events = [f"Error reading EventStream: {e}"]

        response["response"] = events
        return response


def _handle_streaming_response(response) -> Dict[str, Any]:
    complete_text = ""
    for line in response.iter_lines(chunk_size=1):
        if line:
            line = line.decode("utf-8")
            if line.startswith("data: "):
                json_chunk = line[6:]
                try:
                    parsed_chunk = json.loads(json_chunk)
                    if isinstance(parsed_chunk, str):
                        text_chunk = parsed_chunk
                    else:
                        text_chunk = json.dumps(parsed_chunk, ensure_ascii=False)
                        text_chunk += "\n"
                    console.print(text_chunk, end="", style="bold cyan")
                    complete_text += text_chunk
                except json.JSONDecodeError:
                    console.print(json_chunk, style="bold cyan")
                    continue
    console.print()
    return {}


class BedrockAgentCoreClient:
    """Bedrock AgentCore client for agent management."""

    def __init__(self, region: str):
        """Initialize Bedrock AgentCore client.

        Args:
            region: AWS region for the client
        """
        self.region = region
        self.logger = logging.getLogger(f"bedrock_agentcore.runtime.{region}")

        # Get endpoint URLs and log them
        control_plane_url = get_control_plane_endpoint(region)
        data_plane_url = get_data_plane_endpoint(region)

        self.logger.debug("Initializing Bedrock AgentCore client for region: %s", region)
        self.logger.debug("Control plane: %s", control_plane_url)
        self.logger.debug("Data plane: %s", data_plane_url)

        config = Config(
            read_timeout=900,
            connect_timeout=60,
            retries={"max_attempts": 3},
        )

        self.client = boto3.client(
            "bedrock-agentcore-control", region_name=region, endpoint_url=control_plane_url, config=config
        )
        self.dataplane_client = boto3.client(
            "bedrock-agentcore", region_name=region, endpoint_url=data_plane_url, config=config
        )

    def create_agent(
        self,
        agent_name: str,
        image_uri: str,
        execution_role_arn: str,
        network_config: Optional[Dict] = None,
        authorizer_config: Optional[Dict] = None,
        protocol_config: Optional[Dict] = None,
        env_vars: Optional[Dict] = None,
        auto_update_on_conflict: bool = False,
    ) -> Dict[str, str]:
        """Create new agent."""
        self.logger.info("Creating agent '%s' with image URI: %s", agent_name, image_uri)
        try:
            # Build parameters dict, only including optional configs when present
            params = {
                "agentRuntimeName": agent_name,
                "agentRuntimeArtifact": {"containerConfiguration": {"containerUri": image_uri}},
                "roleArn": execution_role_arn,
            }

            if network_config is not None:
                params["networkConfiguration"] = network_config

            if authorizer_config is not None:
                params["authorizerConfiguration"] = authorizer_config

            if protocol_config is not None:
                params["protocolConfiguration"] = protocol_config

            if env_vars is not None:
                params["environmentVariables"] = env_vars

            resp = self.client.create_agent_runtime(**params)
            agent_id = resp["agentRuntimeId"]
            agent_arn = resp["agentRuntimeArn"]
            self.logger.info("Successfully created agent '%s' with ID: %s, ARN: %s", agent_name, agent_id, agent_arn)
            return {"id": agent_id, "arn": agent_arn}
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "ConflictException":
                if not auto_update_on_conflict:
                    self.logger.error("Agent '%s' already exists and auto_update_on_conflict is disabled", agent_name)
                    # Create a more helpful error message
                    raise ClientError(
                        {
                            "Error": {
                                "Code": "ConflictException",
                                "Message": (
                                    f"Agent '{agent_name}' already exists. To update the existing agent, "
                                    "use the --auto-update-on-conflict flag with the launch command."
                                ),
                            }
                        },
                        "CreateAgentRuntime",
                    ) from e

                self.logger.info("Agent '%s' already exists, searching for existing agent...", agent_name)

                # Find existing agent by name
                existing_agent = self.find_agent_by_name(agent_name)

                if not existing_agent:
                    raise RuntimeError(
                        f"ConflictException occurred but couldn't find existing agent '{agent_name}'. "
                        f"This might be a permissions issue or the agent name might be different."
                    ) from e

                # Extract existing agent details
                existing_agent_id = existing_agent["agentRuntimeId"]
                existing_agent_arn = existing_agent["agentRuntimeArn"]

                self.logger.info("Found existing agent ID: %s, updating instead...", existing_agent_id)

                # Update the existing agent
                self.update_agent(
                    existing_agent_id,
                    image_uri,
                    execution_role_arn,
                    network_config,
                    authorizer_config,
                    protocol_config,
                    env_vars,
                )

                # Return the existing agent info (keeping the original ID and ARN)
                return {"id": existing_agent_id, "arn": existing_agent_arn}
            else:
                # Re-raise other ClientErrors
                raise
        except Exception as e:
            self.logger.error("Failed to create agent '%s': %s", agent_name, str(e))
            raise

    def update_agent(
        self,
        agent_id: str,
        image_uri: str,
        execution_role_arn: str,
        network_config: Optional[Dict] = None,
        authorizer_config: Optional[Dict] = None,
        protocol_config: Optional[Dict] = None,
        env_vars: Optional[Dict] = None,
    ) -> Dict[str, str]:
        """Update existing agent."""
        self.logger.info("Updating agent ID '%s' with image URI: %s", agent_id, image_uri)
        try:
            # Build parameters dict, only including optional configs when present
            params = {
                "agentRuntimeId": agent_id,
                "agentRuntimeArtifact": {"containerConfiguration": {"containerUri": image_uri}},
                "roleArn": execution_role_arn,
            }

            if network_config is not None:
                params["networkConfiguration"] = network_config

            if authorizer_config is not None:
                params["authorizerConfiguration"] = authorizer_config

            if protocol_config is not None:
                params["protocolConfiguration"] = protocol_config

            if env_vars is not None:
                params["environmentVariables"] = env_vars

            resp = self.client.update_agent_runtime(**params)
            agent_arn = resp["agentRuntimeArn"]
            self.logger.info("Successfully updated agent ID '%s', ARN: %s", agent_id, agent_arn)
            return {"id": agent_id, "arn": agent_arn}
        except Exception as e:
            self.logger.error("Failed to update agent ID '%s': %s", agent_id, str(e))
            raise

    def list_agents(self, max_results: int = 100) -> list:
        """List all agent runtimes, handling pagination."""
        all_agents = []
        next_token = None

        try:
            while True:
                params = {"maxResults": max_results}
                if next_token:
                    params["nextToken"] = next_token

                response = self.client.list_agent_runtimes(**params)
                agents = response.get("agentRuntimes", [])
                all_agents.extend(agents)

                next_token = response.get("nextToken")
                if not next_token:
                    break

            return all_agents
        except Exception as e:
            self.logger.error("Failed to list agents: %s", str(e))
            raise

    def find_agent_by_name(self, agent_name: str) -> Optional[Dict]:
        """Find an agent by name, reusing list_agents method."""
        try:
            # Get all agents using the existing method
            all_agents = self.list_agents()

            # Search for the specific agent by name
            for agent in all_agents:
                if agent.get("agentRuntimeName") == agent_name:
                    return agent

            return None  # Agent not found
        except Exception as e:
            self.logger.error("Failed to search for agent '%s': %s", agent_name, str(e))
            raise

    def create_or_update_agent(
        self,
        agent_id: Optional[str],
        agent_name: str,
        image_uri: str,
        execution_role_arn: str,
        network_config: Optional[Dict] = None,
        authorizer_config: Optional[Dict] = None,
        protocol_config: Optional[Dict] = None,
        env_vars: Optional[Dict] = None,
        auto_update_on_conflict: bool = False,
    ) -> Dict[str, str]:
        """Create or update agent."""
        if agent_id:
            return self.update_agent(
                agent_id, image_uri, execution_role_arn, network_config, authorizer_config, protocol_config, env_vars
            )
        return self.create_agent(
            agent_name,
            image_uri,
            execution_role_arn,
            network_config,
            authorizer_config,
            protocol_config,
            env_vars,
            auto_update_on_conflict,
        )

    def wait_for_agent_endpoint_ready(self, agent_id: str, endpoint_name: str = "DEFAULT", max_wait: int = 120) -> str:
        """Wait for agent endpoint to be ready.

        Args:
            agent_id: Agent ID to wait for
            endpoint_name: Endpoint name, defaults to "DEFAULT"
            max_wait: Maximum wait time in seconds

        Returns:
            Agent endpoint ARN when ready
        """
        start_time = time.time()

        while time.time() - start_time < max_wait:
            try:
                resp = self.client.get_agent_runtime_endpoint(
                    agentRuntimeId=agent_id,
                    endpointName=endpoint_name,
                )
                status = resp.get("status", "UNKNOWN")

                if status == "READY":
                    return resp["agentRuntimeEndpointArn"]
                elif status in ["CREATE_FAILED", "UPDATE_FAILED"]:
                    raise Exception(
                        f"Agent endpoint {status.lower().replace('_', ' ')}: {resp.get('failureReason', 'Unknown')}"
                    )
                elif status not in ["CREATING", "UPDATING"]:
                    pass
            except self.client.exceptions.ResourceNotFoundException:
                pass
            except Exception as e:
                if "ResourceNotFoundException" not in str(e):
                    raise
            time.sleep(1)
        return (
            f"Endpoint is taking longer than {max_wait} seconds to be ready, "
            f"please check status and try to invoke after some time"
        )

    def get_agent_runtime(self, agent_id: str) -> Dict:
        """Get agent runtime details.

        Args:
            agent_id: Agent ID to get details for

        Returns:
            Agent runtime details
        """
        return self.client.get_agent_runtime(agentRuntimeId=agent_id)

    def get_agent_runtime_endpoint(self, agent_id: str, endpoint_name: str = "DEFAULT") -> Dict:
        """Get agent runtime endpoint details.

        Args:
            agent_id: Agent ID to get endpoint for
            endpoint_name: Endpoint name, defaults to "DEFAULT"

        Returns:
            Agent endpoint details
        """
        return self.client.get_agent_runtime_endpoint(
            agentRuntimeId=agent_id,
            endpointName=endpoint_name,
        )

    def delete_agent_runtime_endpoint(self, agent_id: str, endpoint_name: str = "DEFAULT") -> Dict:
        """Delete agent runtime endpoint.

        Args:
            agent_id: Agent ID to delete endpoint for
            endpoint_name: Endpoint name, defaults to "DEFAULT"

        Returns:
            Response containing the deletion status
        """
        self.logger.info("Deleting agent runtime endpoint '%s' for agent ID: %s", endpoint_name, agent_id)
        try:
            response = self.client.delete_agent_runtime_endpoint(
                agentRuntimeId=agent_id,
                endpointName=endpoint_name,
            )
            self.logger.info("Successfully initiated deletion of endpoint '%s' for agent ID: %s", endpoint_name, agent_id)
            return response
        except Exception as e:
            self.logger.error("Failed to delete endpoint '%s' for agent ID '%s': %s", endpoint_name, agent_id, str(e))
            raise

    def invoke_endpoint(
        self,
        agent_arn: str,
        payload: str,
        session_id: str,
        endpoint_name: str = "DEFAULT",
        user_id: Optional[str] = None,
    ) -> Dict:
        """Invoke agent endpoint."""
        req = {
            "agentRuntimeArn": agent_arn,
            "qualifier": endpoint_name,
            "runtimeSessionId": session_id,
            "payload": payload,
        }

        if user_id:
            req["runtimeUserId"] = user_id

        response = self.dataplane_client.invoke_agent_runtime(**req)
        return _handle_aws_response(response)


class HttpBedrockAgentCoreClient:
    """Bedrock AgentCore client for agent management using HTTP requests with bearer token."""

    def __init__(self, region: str):
        """Initialize HttpBedrockAgentCoreClient.

        Args:
            region: AWS region for the client
        """
        self.region = region
        self.dp_endpoint = get_data_plane_endpoint(region)
        self.logger = logging.getLogger(f"bedrock_agentcore.http_runtime.{region}")

        self.logger.debug("Initializing HTTP Bedrock AgentCore client for region: %s", region)
        self.logger.debug("Data plane: %s", self.dp_endpoint)

    def invoke_endpoint(
        self,
        agent_arn: str,
        payload,
        session_id: str,
        bearer_token: Optional[str],
        endpoint_name: str = "DEFAULT",
    ) -> Dict:
        """Invoke agent endpoint using HTTP request with bearer token.

        Args:
            agent_arn: Agent ARN to invoke
            payload: Payload to send (dict or string)
            session_id: Session ID for the request
            bearer_token: Bearer token for authentication
            endpoint_name: Endpoint name, defaults to "DEFAULT"

        Returns:
            Response from the agent endpoint
        """
        # Escape agent ARN for URL
        escaped_arn = urllib.parse.quote(agent_arn, safe="")

        # Build URL
        url = f"{self.dp_endpoint}/runtimes/{escaped_arn}/invocations"
        # Headers
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
            "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id": session_id,
        }

        # Parse the payload string back to JSON object to send properly
        # This ensures consistent payload structure between boto3 and HTTP clients
        try:
            body = json.loads(payload) if isinstance(payload, str) else payload
        except json.JSONDecodeError:
            # Fallback for non-JSON strings - wrap in payload object
            self.logger.warning("Failed to parse payload as JSON, wrapping in payload object")
            body = {"payload": payload}

        try:
            # Make request with timeout
            response = requests.post(
                url,
                params={"qualifier": endpoint_name},
                headers=headers,
                json=body,
                timeout=900,
                stream=True,
            )
            return _handle_http_response(response)
        except requests.exceptions.RequestException as e:
            self.logger.error("Failed to invoke agent endpoint: %s", str(e))
            raise


class LocalBedrockAgentCoreClient:
    """Local Bedrock AgentCore client for invoking endpoints."""

    def __init__(self, endpoint: str):
        """Initialize the local client with the given endpoint."""
        self.endpoint = endpoint
        self.logger = logging.getLogger("bedrock_agentcore.http_local")

    def invoke_endpoint(self, session_id: str, payload: str, workload_access_token: str):
        """Invoke the endpoint with the given parameters."""
        from bedrock_agentcore.runtime.models import ACCESS_TOKEN_HEADER, SESSION_HEADER

        url = f"{self.endpoint}/invocations"

        headers = {
            "Content-Type": "application/json",
            ACCESS_TOKEN_HEADER: workload_access_token,
            SESSION_HEADER: session_id,
        }

        try:
            body = json.loads(payload) if isinstance(payload, str) else payload
        except json.JSONDecodeError:
            # Fallback for non-JSON strings - wrap in payload object
            self.logger.warning("Failed to parse payload as JSON, wrapping in payload object")
            body = {"payload": payload}

        try:
            # Make request with timeout
            response = requests.post(url, headers=headers, json=body, timeout=900, stream=True)
            return _handle_http_response(response)
        except requests.exceptions.RequestException as e:
            self.logger.error("Failed to invoke agent endpoint: %s", str(e))
            raise
