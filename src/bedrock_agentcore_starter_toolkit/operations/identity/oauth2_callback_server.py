import uvicorn
from pathlib import Path

from bedrock_agentcore.services.identity import IdentityClient, UserIdIdentifier

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.requests import Request
from starlette.responses import JSONResponse

from ...utils.runtime.config import BedrockAgentCoreAgentSchema, load_config

from ...cli.common import console


CALLBACK_3LO_SERVER_PORT = 8081
CALLBACK_ENDPOINT = "/3lo/callback"
WORKLOAD_USER_ID = "userId"


def start_3lo_callback_server(config_path: Path, agent_name: str, debug: bool = False):
    callback_server = BedrockAgentCoreIdentity3loCallback(config_path=config_path, agent_name=agent_name, debug=debug)
    callback_server.run()


class BedrockAgentCoreIdentity3loCallback(Starlette):
    def __init__(self, config_path: Path, agent_name: str, debug: bool = False):
        self.config_path = config_path
        self.agent_name = agent_name
        routes = [
            Route(CALLBACK_ENDPOINT, self._handle_3lo_callback, methods=["GET"]),
        ]
        super().__init__(routes=routes, debug=debug)

    def run(self, **kwargs):
        uvicorn_params = {
            "host": "127.0.0.1",
            "port": CALLBACK_3LO_SERVER_PORT,
            "access_log": self.debug,
            "log_level": "info" if self.debug else "warning",
        }
        uvicorn_params.update(kwargs)

        uvicorn.run(self, **uvicorn_params)

    def _handle_3lo_callback(self, request: Request) -> JSONResponse:
        session_id = request.query_params.get("session_id")
        if not session_id:
            console.print("Missing session_id in OAuth2 3LO callback")
            return JSONResponse(status_code=400, content="missing session_id query parameter")

        project_config = load_config(self.config_path)
        agent_config: BedrockAgentCoreAgentSchema = project_config.get_agent_config(self.agent_name)
        oauth2_config = agent_config.oauth_configuration

        user_id = None
        if oauth2_config:
            user_id = oauth2_config[WORKLOAD_USER_ID]

        if not user_id:
            console.print(f"Missing {WORKLOAD_USER_ID} in Agent OAuth2 Config")
            return JSONResponse(status_code=500, content=None)

        console.print(f"Handling 3LO callback for workload_user_id={user_id} | session_id={session_id}", soft_wrap=True)

        region = agent_config.aws.region
        if not region:
            console.print(f"AWS Region not configured")
            return JSONResponse(status_code=500, content=None)

        identity_client = IdentityClient(region)
        identity_client.complete_resource_token_auth(
            session_uri=session_id, user_identifier=UserIdIdentifier(user_id=user_id)
        )

        return JSONResponse(status_code=200, content=None)

    @classmethod
    def get_callback_endpoint(cls) -> str:
        return f"http://localhost:{CALLBACK_3LO_SERVER_PORT}{CALLBACK_ENDPOINT}"
