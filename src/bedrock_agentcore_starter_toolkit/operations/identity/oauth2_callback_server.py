"""Provides a Starlette-based web server that handles OAuth2 3LO callbacks."""

from pathlib import Path

import uvicorn
from bedrock_agentcore.services.identity import IdentityClient, UserIdIdentifier
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from ...cli.common import console
from ...utils.runtime.config import BedrockAgentCoreAgentSchema, load_config

OAUTH2_CALLBACK_SERVER_PORT = 8081
OAUTH2_CALLBACK_ENDPOINT = "/oauth2/callback"
WORKLOAD_USER_ID = "userId"


def start_oauth2_callback_server(config_path: Path, agent_name: str, debug: bool = False):
    """Starts a server to complete the OAuth2 3LO flow with AgentCore Identity."""
    callback_server = BedrockAgentCoreIdentity3loCallback(config_path=config_path, agent_name=agent_name, debug=debug)
    callback_server.run()


class BedrockAgentCoreIdentity3loCallback(Starlette):
    """Bedrock AgentCore application class that extends Starlette for OAuth2 3LO callback flow."""

    def __init__(self, config_path: Path, agent_name: str, debug: bool = False):
        """Initialize Bedrock AgentCore Identity callback server."""
        self.config_path = config_path
        self.agent_name = agent_name
        routes = [
            Route(OAUTH2_CALLBACK_ENDPOINT, self._handle_3lo_callback, methods=["GET"]),
        ]
        super().__init__(routes=routes, debug=debug)

    def run(self, **kwargs):
        """Start the Bedrock AgentCore Identity OAuth2 callback server."""
        uvicorn_params = {
            "host": "127.0.0.1",
            "port": OAUTH2_CALLBACK_SERVER_PORT,
            "access_log": self.debug,
            "log_level": "info" if self.debug else "warning",
        }
        uvicorn_params.update(kwargs)

        uvicorn.run(self, **uvicorn_params)

    def _handle_3lo_callback(self, request: Request) -> JSONResponse:
        """Handle OAuth2 3LO callbacks with AgentCore Identity."""
        session_id = request.query_params.get("session_id")
        if not session_id:
            console.print("Missing session_id in OAuth2 3LO callback")
            return JSONResponse(status_code=400, content={"message": "missing session_id query parameter"})

        project_config = load_config(self.config_path)
        agent_config: BedrockAgentCoreAgentSchema = project_config.get_agent_config(self.agent_name)
        oauth2_config = agent_config.oauth_configuration

        user_id = None
        if oauth2_config:
            user_id = oauth2_config.get(WORKLOAD_USER_ID)

        if not user_id:
            console.print(f"Missing {WORKLOAD_USER_ID} in Agent OAuth2 Config")
            return JSONResponse(status_code=500, content={"message": "Internal Server Error"})

        console.print(f"Handling 3LO callback for workload_user_id={user_id} | session_id={session_id}", soft_wrap=True)

        region = agent_config.aws.region
        if not region:
            console.print("AWS Region not configured")
            return JSONResponse(status_code=500, content={"message": "Internal Server Error"})

        identity_client = IdentityClient(region)
        identity_client.complete_resource_token_auth(
            session_uri=session_id, user_identifier=UserIdIdentifier(user_id=user_id)
        )

        return JSONResponse(status_code=200, content={"message": "OAuth2 3LO flow completed successfully"})

    @classmethod
    def get_oauth2_callback_endpoint(cls) -> str:
        """Returns the url for the local OAuth2 callback server."""
        return f"http://localhost:{OAUTH2_CALLBACK_SERVER_PORT}{OAUTH2_CALLBACK_ENDPOINT}"
