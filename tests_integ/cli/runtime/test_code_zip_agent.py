import json
import logging
import textwrap
from typing import List

from click.testing import Result

from tests_integ.cli.runtime.base_test import BaseCLIRuntimeTest, CommandInvocation
from tests_integ.utils.config import TEST_ROLE

logger = logging.getLogger("cli-runtime-code-zip-agent-test")


class TestCodeZipAgent(BaseCLIRuntimeTest):
    """
    Test class for code_zip agent CLI runtime tests.
    This class extends BaseCLIRuntimeTest to implement code_zip specific test cases.
    """

    def setup(self):
        # Extract role name from ARN if provided
        if TEST_ROLE:
            self.role_name = TEST_ROLE.split("/")[-1]
        else:
            self.role_name = None

        self.agent_file = "agent.py"
        self.requirements_file = "requirements.txt"

        # Create agent file
        with open(self.agent_file, "w") as f:
            f.write(self.get_agent_code())

        # Create requirements file
        with open(self.requirements_file, "w") as f:
            f.write(self.get_requirements())

    def get_command_invocations(self) -> List[CommandInvocation]:
        """
        Get the list of commands to run for the code_zip agent test.
        """
        # Configure command for code_zip deployment
        configure_cmd = [
            "configure",
            "--name",
            "code_zip_test_agent",
            "--entrypoint",
            self.agent_file,
            "--non-interactive",
        ]
        if TEST_ROLE:
            configure_cmd.extend(["--execution-role", TEST_ROLE])

        # Explicitly specify code_zip deployment type
        configure_cmd.extend(["--deployment-type", "code_zip"])
        configure_cmd.extend(["--requirements-file", self.requirements_file])

        configure_invocation = CommandInvocation(
            command=configure_cmd,
            user_input=[],
            validator=lambda result: self.validate_configure(result),
        )

        launch_invocation = CommandInvocation(
            command=["launch", "--auto-update-on-conflict"],
            user_input=[],
            validator=lambda result: self.validate_launch(result),
        )

        invoke_invocation = CommandInvocation(
            command=["invoke", '{"prompt": "Hello"}'],
            user_input=[],
            validator=lambda result: self.validate_invoke(result),
        )

        status_invocation = CommandInvocation(
            command=["status"],
            user_input=[],
            validator=lambda result: self.validate_status(result),
        )

        destroy_invocation = CommandInvocation(
            command=["destroy", "--force"],
            user_input=[],
            validator=lambda result: self.validate_destroy(result),
        )

        return [configure_invocation, launch_invocation, invoke_invocation, status_invocation, destroy_invocation]

    def get_agent_code(self) -> str:
        """Get the agent code for testing."""
        return textwrap.dedent(
            """
            from bedrock_agentcore import BedrockAgentCoreApp

            app = BedrockAgentCoreApp()

            @app.entrypoint
            def invoke(payload):
                return {"result": "Hello from code_zip agent!"}

            if __name__ == "__main__":
                app.run()
            """
        ).strip()

    def get_requirements(self) -> str:
        """Get the requirements for testing."""
        return "bedrock-agentcore\naws-opentelemetry-distro"

    def validate_configure(self, result: Result):
        output = result.output
        logger.info(output)

        assert "Configuration Success" in output
        assert "Agent Name: code_zip_test_agent" in output

        # Handle both explicit role and auto-create
        if TEST_ROLE:
            assert TEST_ROLE in output
        else:
            assert "Auto-create" in output or "Execution Role:" in output

        assert "Authorization: IAM" in output
        assert ".bedrock_agentcore.yaml" in output

        # Code_zip specific validations
        assert "Deployment: code_zip" in output
        assert "S3 Bucket: Auto-create" in output
        assert "ECR Repository: N/A" in output

    def validate_launch(self, result: Result):
        output = result.output
        logger.info(output)

        # Code_zip specific launch validations
        assert "Launching Bedrock AgentCore (cloud mode" in output
        assert "Deploy Python code directly to runtime" in output
        assert "No Docker required" in output
        assert "Deployment Success" in output
        assert "Deployment Type: Code Zip (Lambda-style)" in output
        assert "Code package deployed to Bedrock AgentCore" in output

    def validate_invoke(self, result: Result):
        output = result.output
        logger.info(output)

        # Parse JSON response
        try:
            response = json.loads(output)
            assert "result" in response
            assert "Hello from code_zip agent!" in response["result"]
        except json.JSONDecodeError:
            # Fallback: check for expected text in output
            assert "Hello from code_zip agent!" in output

    def validate_status(self, result: Result):
        output = result.output
        logger.info(output)

        assert "Agent Name: code_zip_test_agent" in output
        assert "Status: ACTIVE" in output or "RUNNING" in output or "READY" in output

    def validate_destroy(self, result: Result):
        output = result.output
        logger.info(output)

        assert "About to destroy resources" in output


def test(tmp_path):
    """
    Run the code_zip agent CLI test.
    This function is the entry point for the test.
    """
    TestCodeZipAgent().run(tmp_path)
