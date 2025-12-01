import logging
import os
import re
from pathlib import Path
from typing import List
from unittest.mock import patch

from click.testing import Result

from tests_integ.cli.runtime.base_test import BaseCLIRuntimeTest, CommandInvocation

logger = logging.getLogger("cli-identity-aws-jwt-test")


def _strip_ansi(text: str) -> str:
    """Remove ANSI color codes from text."""
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_escape.sub("", text)


class TestIdentityAwsJwt(BaseCLIRuntimeTest):
    """
    Test class for Identity service AWS JWT federation commands.
    Tests the AWS JWT setup and configuration flow.
    """

    def setup(self):
        """Setup for AWS JWT flow test."""
        self.audience = "https://api.example.com"
        self.issuer_url = None

    def get_command_invocations(self) -> List[CommandInvocation]:
        """Test AWS JWT-specific commands."""
        return [
            # Step 1: Configure agent first
            CommandInvocation(
                command=[
                    "configure",
                    "--entrypoint",
                    "agent.py",
                    "--name",
                    "aws_jwt_test",
                    "--requirements-file",
                    "requirements.txt",
                    "--non-interactive",
                    "--disable-memory",
                ],
                user_input=[],
                validator=lambda result: self.validate_configure(result),
            ),
            # Step 2: Setup AWS JWT federation
            CommandInvocation(
                command=[
                    "identity",
                    "setup-aws-jwt",
                    "--audience",
                    self.audience,
                    "--signing-algorithm",
                    "ES384",
                    "--duration",
                    "300",
                ],
                user_input=[],
                validator=lambda result: self.validate_setup_aws_jwt(result),
            ),
            # Step 3: List AWS JWT configuration
            CommandInvocation(
                command=["identity", "list-aws-jwt"],
                user_input=[],
                validator=lambda result: self.validate_list_aws_jwt(result),
            ),
            # Step 4: Add another audience
            CommandInvocation(
                command=[
                    "identity",
                    "setup-aws-jwt",
                    "--audience",
                    "https://api2.example.com",
                ],
                user_input=[],
                validator=lambda result: self.validate_add_audience(result),
            ),
            # Step 5: List again to verify both audiences
            CommandInvocation(
                command=["identity", "list-aws-jwt"],
                user_input=[],
                validator=lambda result: self.validate_list_multiple_audiences(result),
            ),
            # Step 6: Verify config file
            CommandInvocation(
                command=[],  # Empty command = just validation
                user_input=[],
                validator=lambda result: self.validate_config_file(result),
            ),
        ]

    def run(self, tmp_path) -> None:
        """Override run to create agent file and handle empty commands."""
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Create a simple agent file for configure
            agent_file = tmp_path / "agent.py"
            agent_file.write_text("""
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

@app.entrypoint
async def invoke(payload, context):
    return {"response": "test"}

if __name__ == "__main__":
    app.run()
""")

            # Create requirements.txt file
            requirements_file = tmp_path / "requirements.txt"
            requirements_file.write_text("""bedrock-agentcore
boto3
""")

            from prompt_toolkit.application import create_app_session
            from prompt_toolkit.input import create_pipe_input
            from typer.testing import CliRunner

            from bedrock_agentcore_starter_toolkit.cli.cli import app

            runner = CliRunner()
            self.setup()
            command_invocations = self.get_command_invocations()

            for _idx, command_invocation in enumerate(command_invocations):
                command = command_invocation.command
                input_data = command_invocation.user_input
                validator = command_invocation.validator

                # Skip empty commands (used for file validation only)
                if not command:
                    validator(None)
                    continue

                logger.info("Running command %s with input %s", command, input_data)

                with create_pipe_input() as pipe_input:
                    with create_app_session(input=pipe_input):
                        for data in input_data:
                            pipe_input.send_text(data + "\n")

                        # Mock the AWS JWT federation setup for commands that need it
                        if "setup-aws-jwt" in command:
                            with patch(
                                "bedrock_agentcore_starter_toolkit.cli.identity.commands.setup_aws_jwt_federation"
                            ) as mock_setup:
                                mock_setup.return_value = (True, "https://sts.us-west-2.amazonaws.com")
                                result = runner.invoke(app, args=command)
                        else:
                            result = runner.invoke(app, args=command)

                validator(result)
        finally:
            os.chdir(original_dir)

    def validate_configure(self, result: Result):
        """Validate agent configuration."""
        output = _strip_ansi(result.output)
        logger.info(output)

        assert result.exit_code == 0, f"Configure failed: {output}"
        assert "Configuration Success" in output or "aws_jwt_test" in output

    def validate_setup_aws_jwt(self, result: Result):
        """Validate AWS JWT setup output."""
        output = _strip_ansi(result.output)
        logger.info(output)

        assert result.exit_code == 0, f"Setup AWS JWT failed: {output}"
        assert "AWS JWT Federation Configured" in output or "Success" in output
        assert self.audience in output
        assert "ES384" in output

        # Extract issuer URL for later validation
        if "Issuer URL:" in output:
            # Parse issuer URL from output
            for line in output.split("\n"):
                if "sts" in line.lower() and "amazonaws.com" in line.lower():
                    self.issuer_url = line.strip()
                    break

    def validate_list_aws_jwt(self, result: Result):
        """Validate list AWS JWT output."""
        output = _strip_ansi(result.output)
        logger.info(output)

        assert result.exit_code == 0, f"List AWS JWT failed: {output}"
        assert "AWS JWT Federation Configuration" in output
        assert "Yes" in output  # Enabled
        assert "ES384" in output
        assert "300" in output
        assert self.audience in output

    def validate_add_audience(self, result: Result):
        """Validate adding another audience."""
        output = _strip_ansi(result.output)
        logger.info(output)

        assert result.exit_code == 0, f"Add audience failed: {output}"
        assert "Added audience" in output or "https://api2.example.com" in output

    def validate_list_multiple_audiences(self, result: Result):
        """Validate listing with multiple audiences."""
        output = _strip_ansi(result.output)
        logger.info(output)

        assert result.exit_code == 0, f"List failed: {output}"
        assert self.audience in output
        assert "https://api2.example.com" in output

    def validate_config_file(self, result: Result):
        """Validate config file contents."""
        config_path = Path(".bedrock_agentcore.yaml")
        assert config_path.exists(), "Config file not found"

        from bedrock_agentcore_starter_toolkit.utils.runtime.config import load_config

        project_config = load_config(config_path)
        agent_config = project_config.get_agent_config()

        # Verify AWS JWT config
        assert agent_config.identity is not None
        assert agent_config.identity.aws_jwt is not None
        assert agent_config.identity.aws_jwt.enabled is True
        assert self.audience in agent_config.identity.aws_jwt.audiences
        assert "https://api2.example.com" in agent_config.identity.aws_jwt.audiences
        assert agent_config.identity.aws_jwt.signing_algorithm == "ES384"
        assert agent_config.identity.aws_jwt.duration_seconds == 300

        logger.info("✅ Config file validation passed")


class TestIdentityAwsJwtValidation(BaseCLIRuntimeTest):
    """
    Test class for AWS JWT input validation.
    Tests error handling for invalid inputs.
    """

    def setup(self):
        """Setup for validation tests."""
        pass

    def get_command_invocations(self) -> List[CommandInvocation]:
        """Test validation error cases."""
        return [
            # Test invalid signing algorithm
            CommandInvocation(
                command=[
                    "identity",
                    "setup-aws-jwt",
                    "--audience",
                    "https://api.example.com",
                    "--signing-algorithm",
                    "INVALID",
                ],
                user_input=[],
                validator=lambda result: self.validate_invalid_algorithm(result),
            ),
            # Test duration too short
            CommandInvocation(
                command=[
                    "identity",
                    "setup-aws-jwt",
                    "--audience",
                    "https://api.example.com",
                    "--duration",
                    "30",
                ],
                user_input=[],
                validator=lambda result: self.validate_duration_too_short(result),
            ),
            # Test duration too long
            CommandInvocation(
                command=[
                    "identity",
                    "setup-aws-jwt",
                    "--audience",
                    "https://api.example.com",
                    "--duration",
                    "7200",
                ],
                user_input=[],
                validator=lambda result: self.validate_duration_too_long(result),
            ),
        ]

    def validate_invalid_algorithm(self, result: Result):
        """Validate error for invalid signing algorithm."""
        output = _strip_ansi(result.output)
        logger.info(output)

        assert result.exit_code != 0, "Should have failed for invalid algorithm"
        assert "ES384" in output or "RS256" in output

    def validate_duration_too_short(self, result: Result):
        """Validate error for duration too short."""
        output = _strip_ansi(result.output)
        logger.info(output)

        assert result.exit_code != 0, "Should have failed for short duration"
        assert "60" in output or "between" in output.lower()

    def validate_duration_too_long(self, result: Result):
        """Validate error for duration too long."""
        output = _strip_ansi(result.output)
        logger.info(output)

        assert result.exit_code != 0, "Should have failed for long duration"
        assert "3600" in output or "between" in output.lower()


def test_identity_aws_jwt_flow(tmp_path):
    """
    Test Identity service with AWS JWT federation flow.
    """
    TestIdentityAwsJwt().run(tmp_path)


def test_identity_aws_jwt_validation(tmp_path):
    """
    Test AWS JWT input validation.
    """
    TestIdentityAwsJwtValidation().run(tmp_path)
