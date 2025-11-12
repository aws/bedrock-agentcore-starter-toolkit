import json
import logging
import os
import re
import textwrap
import uuid
from typing import List

from click.testing import Result

from tests_integ.cli.runtime.base_test import BaseCLIRuntimeTest, CommandInvocation

logger = logging.getLogger("cli-identity-flow-test")


def _strip_ansi(text: str) -> str:
    """Remove ANSI color codes from text."""
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_escape.sub("", text)


class TestIdentityFlow(BaseCLIRuntimeTest):
    """
    Test class for Identity service CLI commands.
    Tests the complete OAuth2 authentication flow with Cognito.
    """

    def setup(self):
        """Setup test files and environment."""
        self.agent_file = "identity_agent.py"
        self.requirements_file = "requirements.txt"
        self.auth_flow = "user"  # Test USER_FEDERATION flow
        self.provider_name = f"TestProvider-{uuid.uuid4().hex[:8]}"
        self.workload_name = f"test-workload-{uuid.uuid4().hex[:8]}"

        # Track created resources for cleanup
        self.runtime_pool_id = None
        self.identity_pool_id = None
        self.runtime_client_id = None
        self.identity_client_id = None
        self.identity_client_secret = None
        self.runtime_discovery_url = None
        self.identity_discovery_url = None
        self.runtime_username = None
        self.runtime_password = None
        self.bearer_token = None

        # Create agent file with Identity integration
        with open(self.agent_file, "w") as file:
            content = textwrap.dedent("""
                from strands import Agent
                from bedrock_agentcore.runtime import BedrockAgentCoreApp
                from bedrock_agentcore.identity.auth import requires_access_token

                app = BedrockAgentCoreApp()
                agent = Agent()

                auth_url_holder = {"url": None}

                @requires_access_token(
                    provider_name="TestProvider",
                    scopes=["openid"],
                    auth_flow="USER_FEDERATION",
                    on_auth_url=lambda url: auth_url_holder.update({"url": url}),
                    force_authentication=True
                )
                async def get_external_token(*, access_token: str) -> str:
                    return access_token

                @app.entrypoint
                async def invoke(payload, context):
                    try:
                        auth_url_holder["url"] = None
                        import asyncio
                        try:
                            token = await asyncio.wait_for(get_external_token(), timeout=2.0)
                        except asyncio.TimeoutError:
                            if auth_url_holder["url"]:
                                return {"response": f"Authorization required: {auth_url_holder['url']}"}
                            return {"response": "Timeout waiting for authentication"}

                        if auth_url_holder["url"]:
                            return {"response": f"Authorization required: {auth_url_holder['url']}"}

                        return {"response": f"Success! Token obtained (length: {len(token)})"}
                    except Exception as e:
                        return {"response": f"Error: {str(e)}"}

                if __name__ == "__main__":
                    app.run()
            """).strip()
            file.write(content)

        # Create requirements file
        with open(self.requirements_file, "w") as file:
            content = textwrap.dedent("""
                bedrock-agentcore
                bedrock-agentcore-starter-toolkit
                strands-agents
                boto3
            """).strip()
            file.write(content)

    def get_command_invocations(self) -> List[CommandInvocation]:
        """Define the sequence of commands to test Identity flow."""
        return [
            # Step 1: Setup Cognito pools
            CommandInvocation(
                command=[
                    "identity",
                    "setup-cognito",
                    "--auth-flow",
                    self.auth_flow,
                ],
                user_input=[],
                validator=lambda result: self.validate_setup_cognito(result),
            ),
            # Step 2: Configure agent with JWT auth
            CommandInvocation(
                command=[
                    "configure",
                    "--entrypoint",
                    self.agent_file,
                    "--name",
                    "identity_test",
                    "--requirements-file",
                    self.requirements_file,
                    "--non-interactive",
                    "--disable-memory",
                ],
                user_input=[],
                validator=lambda result: self.validate_configure(result),
            ),
            # Step 3: Add JWT authorizer configuration
            CommandInvocation(
                command=["configure"],  # Will be modified in pre-execution
                user_input=[],
                validator=lambda result: self.validate_jwt_config(result),
            ),
            # Step 4: Create credential provider
            CommandInvocation(
                command=["identity", "create-credential-provider"],  # Will be modified
                user_input=[],
                validator=lambda result: self.validate_create_provider(result),
            ),
            # Step 5: Create workload identity
            CommandInvocation(
                command=[
                    "identity",
                    "create-workload-identity",
                    "--name",
                    self.workload_name,
                    "--callback-urls",
                    "http://localhost:8081/oauth2/callback",
                ],
                user_input=[],
                validator=lambda result: self.validate_create_workload(result),
            ),
            # Step 6: List providers
            CommandInvocation(
                command=["identity", "list-providers"],
                user_input=[],
                validator=lambda result: self.validate_list_providers(result),
            ),
            # Step 7: Deploy agent
            CommandInvocation(
                command=["launch", "--auto-update-on-conflict"],
                user_input=[],
                validator=lambda result: self.validate_launch(result),
            ),
            # Step 8: Get bearer token
            CommandInvocation(
                command=["identity", "get-inbound-token"],  # Will be modified
                user_input=[],
                validator=lambda result: self.validate_get_token(result),
            ),
            # Step 9: Invoke with bearer token (expect auth URL)
            CommandInvocation(
                command=["invoke", '{"prompt": "test"}'],  # Will add --bearer-token
                user_input=[],
                validator=lambda result: self.validate_invoke_with_auth_url(result),
            ),
            # Step 10: Cleanup
            CommandInvocation(
                command=[
                    "identity",
                    "cleanup",
                    "--agent",
                    "identity_test",
                    "--force",
                ],
                user_input=[],
                validator=lambda result: self.validate_cleanup(result),
            ),
        ]

    def run(self, tmp_path) -> None:
        """Override run to handle dynamic command building and skip empty commands."""
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)
            from prompt_toolkit.application import create_app_session
            from prompt_toolkit.input import create_pipe_input
            from typer.testing import CliRunner

            from bedrock_agentcore_starter_toolkit.cli.cli import app

            runner = CliRunner()
            self.setup()
            command_invocations = self.get_command_invocations()

            for idx, command_invocation in enumerate(command_invocations):
                command = command_invocation.command
                input_data = command_invocation.user_input
                validator = command_invocation.validator

                # Modify commands that need Cognito details
                if idx == 2:  # JWT config step
                    command = self._build_jwt_config_command()
                elif idx == 3:  # Create credential provider
                    command = self._build_create_provider_command()
                elif idx == 7:  # Get inbound token
                    command = self._build_get_token_command()
                elif idx == 8:  # Invoke with bearer token
                    command = self._build_invoke_command()

                # Skip empty commands (used for file validation only)
                if not command:
                    validator(None)  # ← Pass None for result
                    continue

                logger.info("Running command %s with input %s", command, input_data)

                with create_pipe_input() as pipe_input:
                    with create_app_session(input=pipe_input):
                        for data in input_data:
                            pipe_input.send_text(data + "\n")

                        result = runner.invoke(app, args=command)

                validator(result)
        finally:
            os.chdir(original_dir)

    def _load_cognito_config(self):
        """Load Cognito configuration from saved file."""
        config_file = f".agentcore_identity_cognito_{self.auth_flow}.json"
        if os.path.exists(config_file):
            with open(config_file) as f:
                return json.load(f)
        return None

    def _build_jwt_config_command(self) -> List[str]:
        """Build configure command with JWT authorizer."""
        cognito_config = self._load_cognito_config()
        if not cognito_config:
            raise RuntimeError("Cognito config not found")

        self.runtime_discovery_url = cognito_config["runtime"]["discovery_url"]
        self.runtime_client_id = cognito_config["runtime"]["client_id"]

        authorizer_json = json.dumps(
            {
                "customJWTAuthorizer": {
                    "discoveryUrl": self.runtime_discovery_url,
                    "allowedClients": [self.runtime_client_id],
                }
            }
        )

        return [
            "configure",
            "--entrypoint",
            self.agent_file,
            "--name",
            "identity_test",
            "--authorizer-config",
            authorizer_json,
            "--non-interactive",
        ]

    def _build_create_provider_command(self) -> List[str]:
        """Build create-credential-provider command."""
        cognito_config = self._load_cognito_config()
        if not cognito_config:
            raise RuntimeError("Cognito config not found")

        self.identity_pool_id = cognito_config["identity"]["pool_id"]
        self.identity_client_id = cognito_config["identity"]["client_id"]
        self.identity_client_secret = cognito_config["identity"]["client_secret"]
        self.identity_discovery_url = cognito_config["identity"]["discovery_url"]

        return [
            "identity",
            "create-credential-provider",
            "--name",
            self.provider_name,
            "--type",
            "cognito",
            "--client-id",
            self.identity_client_id,
            "--client-secret",
            self.identity_client_secret,
            "--discovery-url",
            self.identity_discovery_url,
            "--cognito-pool-id",
            self.identity_pool_id,
        ]

    def _build_get_token_command(self) -> List[str]:
        """Build get-inbound-token command."""
        cognito_config = self._load_cognito_config()
        if not cognito_config:
            raise RuntimeError("Cognito config not found")

        self.runtime_pool_id = cognito_config["runtime"]["pool_id"]
        self.runtime_username = cognito_config["runtime"]["username"]
        self.runtime_password = cognito_config["runtime"]["password"]

        return [
            "identity",
            "get-inbound-token",
            "--pool-id",
            self.runtime_pool_id,
            "--client-id",
            self.runtime_client_id,
            "--username",
            self.runtime_username,
            "--password",
            self.runtime_password,
        ]

    def _build_invoke_command(self) -> List[str]:
        """Build invoke command with bearer token."""
        # Token would be captured from previous command output
        # For now, we'll regenerate it inline
        return [
            "invoke",
            '{"prompt": "test"}',
            "--bearer-token",
            self.bearer_token,
        ]

    # Validation methods
    def validate_setup_cognito(self, result: Result):
        """Validate Cognito setup output."""
        output = result.output
        logger.info(output)

        assert result.exit_code == 0, f"Command failed with exit code {result.exit_code}"
        assert "Cognito pools created successfully" in output
        assert "Runtime Pool" in output
        assert "Identity Pool" in output
        assert "Pool ID:" in output
        assert "Client ID:" in output
        assert "Discovery URL:" in output
        assert "Test User:" in output

        # Verify files created
        assert os.path.exists(f".agentcore_identity_cognito_{self.auth_flow}.json")
        assert os.path.exists(f".agentcore_identity_{self.auth_flow}.env")

    def validate_configure(self, result: Result):
        """Validate agent configuration."""
        output = _strip_ansi(result.output)  # ← Strip colors
        logger.info(output)

        assert result.exit_code == 0
        assert "Configuration Success" in output
        assert "Agent Name: identity_test" in output

    def validate_jwt_config(self, result: Result):
        """Validate JWT authorizer configuration."""
        output = result.output
        logger.info(output)

        assert result.exit_code == 0
        assert "Configuration Success" in output or "Updated" in output
        assert "OAuth (customJWTAuthorizer)" in output or "Authorization" in output

    def validate_create_provider(self, result: Result):
        """Validate credential provider creation."""
        output = _strip_ansi(result.output)  # ← Strip colors
        logger.info(output)

        assert result.exit_code == 0
        assert "Credential Provider Created" in output or "Created credential provider" in output
        assert self.provider_name in output
        assert "cognito" in output.lower()
        assert "Configuration saved to .bedrock_agentcore.yaml" in output

    def validate_create_workload(self, result: Result):
        """Validate workload identity creation."""
        output = result.output
        logger.info(output)

        assert result.exit_code == 0
        assert "Workload Identity Created" in output or "Created" in output
        assert self.workload_name in output
        assert "http://localhost:8081/oauth2/callback" in output

    def validate_list_providers(self, result: Result):
        """Validate list providers output."""
        output = _strip_ansi(result.output)
        logger.info(output)

        assert result.exit_code == 0
        assert self.provider_name in output
        assert "cognito" in output.lower()
        assert "Workload Identity:" in output or self.workload_name in output

    def validate_launch(self, result: Result):
        """Validate agent launch."""
        output = result.output
        logger.info(output)

        assert result.exit_code == 0
        assert "Deployment Success" in output or "deployed" in output.lower()
        assert "identity_test" in output

    def validate_get_token(self, result: Result):
        """Validate token retrieval."""
        output = result.output
        logger.info(output)

        assert result.exit_code == 0
        # Token should be printed (JWT format: header.payload.signature)
        assert "." in output  # JWT has dots
        assert len(output.strip()) > 50  # JWT tokens are long

        # Extract the token
        self.bearer_token = output.strip()
        logger.info("Captured bearer token: %s...", self.bearer_token[:50])

    def validate_invoke_with_auth_url(self, result: Result):
        """Validate invocation returns authorization URL."""
        output = result.output
        logger.info(output)

        # First invocation should return authorization URL
        # (We can't complete the browser flow in automated tests)
        assert "Session:" in output
        assert "Request ID:" in output or "Authorization required" in output

    def validate_cleanup(self, result: Result):
        """Validate cleanup."""
        output = result.output
        logger.info(output)

        assert result.exit_code == 0
        assert "cleanup complete" in output.lower() or "deleted" in output.lower()

        # Verify files removed
        assert not os.path.exists(f".agentcore_identity_cognito_{self.auth_flow}.json")
        assert not os.path.exists(f".agentcore_identity_{self.auth_flow}.env")


def test_identity_user_flow(tmp_path):
    """
    Test Identity service with USER_FEDERATION flow.
    """
    TestIdentityFlow().run(tmp_path)
