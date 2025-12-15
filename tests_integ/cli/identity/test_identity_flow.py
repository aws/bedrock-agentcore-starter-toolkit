import json
import logging
import os
import re
import textwrap
import uuid
from typing import List

import pytest
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
    Tests the OAuth2 configuration flow (without actual deployment).
    """

    def setup(self):
        """Setup test files and environment."""
        self.agent_file = "identity_agent.py"
        self.requirements_file = "requirements.txt"
        self.auth_flow = "user"

        test_id = uuid.uuid4().hex[:8]
        self.agent_name = f"identity_test_{test_id}"
        self.provider_name = f"TestProvider_{test_id}"
        self.workload_name = f"test_workload_{test_id}"

        # Create agent file
        with open(self.agent_file, "w") as file:
            content = textwrap.dedent("""
                from bedrock_agentcore.runtime import BedrockAgentCoreApp

                app = BedrockAgentCoreApp()

                @app.entrypoint
                async def invoke(payload, context):
                    return {"response": "test"}

                if __name__ == "__main__":
                    app.run()
            """).strip()
            file.write(content)

        # Create requirements file
        with open(self.requirements_file, "w") as file:
            file.write("bedrock-agentcore\nboto3\n")

    def get_command_invocations(self) -> List[CommandInvocation]:
        """Define the sequence of commands to test Identity flow (config only)."""
        return [
            # Step 1: Setup Cognito pools
            CommandInvocation(
                command=["identity", "setup-cognito", "--auth-flow", self.auth_flow],
                user_input=[],
                validator=lambda result: self.validate_setup_cognito(result),
            ),
            # Step 2: Configure agent
            CommandInvocation(
                command=[
                    "configure",
                    "--entrypoint",
                    self.agent_file,
                    "--name",
                    self.agent_name,
                    "--requirements-file",
                    self.requirements_file,
                    "--non-interactive",
                    "--disable-memory",
                ],
                user_input=[],
                validator=lambda result: self.validate_configure(result),
            ),
            # Step 3: Add JWT authorizer
            CommandInvocation(
                command=["configure"],  # Will be modified
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
                    "--return-urls",
                    "http://localhost:8081/oauth2/callback",
                ],
                user_input=[],
                validator=lambda result: self.validate_create_workload(result),
            ),
            # Step 6: List providers
            CommandInvocation(
                command=["identity", "list-credential-providers"],
                user_input=[],
                validator=lambda result: self.validate_list_providers(result),
            ),
            # REMOVED: launch, invoke, get-token steps (they hang in CI/tests)
            # Step 7: Cleanup
            CommandInvocation(
                command=["identity", "cleanup", "--agent", self.agent_name, "--force"],
                user_input=[],
                validator=lambda result: self.validate_cleanup(result),
            ),
        ]

    def run(self, tmp_path) -> None:
        """Override run to handle dynamic command building."""
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
                if idx == 2:  # JWT config
                    command = self._build_jwt_config_command()
                elif idx == 3:  # Create credential provider
                    command = self._build_create_provider_command()

                if not command:
                    validator(None)
                    continue

                logger.info("Step %s: Running command %s", idx, command)

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
            self.agent_name,
            "--authorizer-config",
            authorizer_json,
            "--non-interactive",
        ]

    def _build_create_provider_command(self) -> List[str]:
        """Build create-credential-provider command."""
        cognito_config = self._load_cognito_config()
        if not cognito_config:
            raise RuntimeError("Cognito config not found")

        return [
            "identity",
            "create-credential-provider",
            "--name",
            self.provider_name,
            "--type",
            "cognito",
            "--client-id",
            cognito_config["identity"]["client_id"],
            "--client-secret",
            cognito_config["identity"]["client_secret"],
            "--discovery-url",
            cognito_config["identity"]["discovery_url"],
            "--cognito-pool-id",
            cognito_config["identity"]["pool_id"],
        ]

    # Validation methods
    def validate_setup_cognito(self, result: Result):
        output = result.output
        logger.info(output)
        assert result.exit_code == 0, f"Setup Cognito failed:\n{output}"
        assert "Cognito pools created successfully" in output

    def validate_configure(self, result: Result):
        output = _strip_ansi(result.output)
        logger.info(output)
        assert result.exit_code == 0, f"Configure failed:\n{output}"
        assert "Configuration Success" in output

    def validate_jwt_config(self, result: Result):
        output = result.output
        logger.info(output)
        assert result.exit_code == 0, f"JWT config failed:\n{output}"

    def validate_create_provider(self, result: Result):
        output = _strip_ansi(result.output)
        logger.info(output)
        assert result.exit_code == 0, f"Create provider failed:\n{output}"
        assert "Credential Provider Created" in output or "Created" in output

    def validate_create_workload(self, result: Result):
        output = result.output
        logger.info(output)
        assert result.exit_code == 0, f"Create workload failed:\n{output}"
        assert "Workload Identity Created" in output or "Created" in output

    def validate_list_providers(self, result: Result):
        output = _strip_ansi(result.output)
        logger.info(output)
        assert result.exit_code == 0, f"List providers failed:\n{output}"
        assert "TestProvider" in output
        assert "cognito" in output.lower()

    def validate_cleanup(self, result: Result):
        output = result.output
        logger.info(output)
        assert result.exit_code == 0, f"Cleanup failed:\n{output}"


@pytest.mark.timeout(300)  # 5 minute timeout
def test_identity_user_flow(tmp_path):
    """Test Identity service with USER_FEDERATION flow (config only)."""
    TestIdentityFlow().run(tmp_path)
