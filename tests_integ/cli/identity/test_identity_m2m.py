import json
import logging
import os
import re
from typing import List

from click.testing import Result

from tests_integ.cli.runtime.base_test import BaseCLIRuntimeTest, CommandInvocation

logger = logging.getLogger("cli-identity-m2m-test")


def _strip_ansi(text: str) -> str:
    """Remove ANSI color codes from text."""
    ansi_escape = re.compile(r"\x1b\[[0-9;]*m")
    return ansi_escape.sub("", text)


class TestIdentityM2M(BaseCLIRuntimeTest):
    """
    Test class for Identity service with M2M (client credentials) flow.
    Tests only the Cognito setup without full agent deployment.
    """

    def setup(self):
        """Setup for M2M flow test."""
        self.auth_flow = "m2m"
        self.runtime_pool_id = None
        self.identity_pool_id = None

    def get_command_invocations(self) -> List[CommandInvocation]:
        """Test M2M-specific commands."""
        return [
            # Step 1: Setup Cognito with M2M flow
            CommandInvocation(
                command=[
                    "identity",
                    "setup-cognito",
                    "--auth-flow",
                    "m2m",
                ],
                user_input=[],
                validator=lambda result: self.validate_setup_m2m(result),
            ),
            # Step 2: Verify config file structure (no command to run)
            CommandInvocation(
                command=[],  # Empty command = just validation
                user_input=[],
                validator=lambda result: self.validate_m2m_config_file(result),
            ),
            # Step 3: Manual cleanup (cleanup command needs agent config)
            CommandInvocation(
                command=[],  # Empty command = manual cleanup
                user_input=[],
                validator=lambda result: self.validate_cleanup_m2m(result),
            ),
        ]

    def validate_setup_m2m(self, result: Result):
        """Validate M2M Cognito setup."""
        output = _strip_ansi(result.output)
        logger.info(output)

        assert result.exit_code == 0
        assert "Cognito pools created successfully" in output
        assert "M2M" in output or "CLIENT_CREDENTIALS" in output.upper()
        assert "Resource Server:" in output
        assert "Token Endpoint:" in output

        # Verify M2M config files exist
        assert os.path.exists(".agentcore_identity_cognito_m2m.json")
        assert os.path.exists(".agentcore_identity_m2m.env")

        # Store pool IDs for cleanup
        with open(".agentcore_identity_cognito_m2m.json") as f:
            config = json.load(f)
            self.runtime_pool_id = config["runtime"]["pool_id"]
            self.identity_pool_id = config["identity"]["pool_id"]

    def validate_m2m_config_file(self, result: Result):
        """Validate M2M config file structure (no command to run)."""
        # Verify file contents
        with open(".agentcore_identity_cognito_m2m.json") as f:
            config = json.load(f)

            # Check top-level flow type
            assert config.get("flow_type") == "m2m", f"Expected flow_type 'm2m', got {config.get('flow_type')}"

            # Check identity section
            assert "identity" in config
            assert "token_endpoint" in config["identity"]
            assert "resource_server_identifier" in config["identity"]
            assert "scopes" in config["identity"]
            assert isinstance(config["identity"]["scopes"], list)

            # Check identity flow type (nested)
            assert config["identity"].get("flow_type") == "client_credentials"

            # Verify runtime pool also created
            assert "runtime" in config
            assert "pool_id" in config["runtime"]
            assert "client_id" in config["runtime"]
            assert "discovery_url" in config["runtime"]

    def validate_cleanup_m2m(self, result: Result):
        """Manual cleanup of Cognito pools and config files."""
        logger.info("Performing manual cleanup of Cognito pools...")

        try:
            # Use IdentityCognitoManager to cleanup
            from bedrock_agentcore_starter_toolkit.operations.identity.helpers import IdentityCognitoManager

            region = os.getenv("AWS_DEFAULT_REGION", "us-west-2")
            manager = IdentityCognitoManager(region)

            # Delete both pools
            manager.cleanup_cognito_pools(runtime_pool_id=self.runtime_pool_id, identity_pool_id=self.identity_pool_id)

            logger.info("✓ Deleted Cognito pools")

        except Exception as e:
            logger.warning("Error during Cognito cleanup: %s", e)

        # Delete config files
        for file in [".agentcore_identity_cognito_m2m.json", ".agentcore_identity_m2m.env"]:
            if os.path.exists(file):
                os.remove(file)
                logger.info("✓ Deleted %s", file)

        # Verify cleanup
        assert not os.path.exists(".agentcore_identity_cognito_m2m.json")
        assert not os.path.exists(".agentcore_identity_m2m.env")

        logger.info("✅ M2M cleanup complete")


def test_identity_m2m_flow(tmp_path):
    """
    Test Identity service with M2M (client credentials) flow.
    """
    TestIdentityM2M().run(tmp_path)
