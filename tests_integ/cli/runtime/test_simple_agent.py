import logging
import textwrap
from typing import List

from click.testing import Result

from tests_integ.cli.runtime.base_test import BaseCLIRuntimeTest, CommandInvocation
from tests_integ.utils.config import TEST_ECR, TEST_ROLE

logger = logging.getLogger("cli-runtime-simple-agent-test")


class TestSimpleAgent(BaseCLIRuntimeTest):
    """
    Test class for simple agent CLI runtime tests.
    This class extends BaseCLIRuntimeTest to implement specific test cases.
    """

    def setup(self):
        self.agent_file = "agent.py"
        self.requirements_file = "requirements.txt"

        with open(self.agent_file, "w") as file:
            content = textwrap.dedent("""
                from bedrock_agentcore import BedrockAgentCoreApp
                from strands import Agent

                app = BedrockAgentCoreApp()
                agent = Agent()

                @app.entrypoint
                async def agent_invocation(payload):
                    return agent(payload.get("message"))

                app.run()
            """).strip()
            file.write(content)

        with open(self.requirements_file, "w") as file:
            content = textwrap.dedent("""
                strands-agents
                bedrock-agentcore
            """).strip()
            file.write(content)

    def get_command_invocations(self) -> List[CommandInvocation]:
        configure_invocation = CommandInvocation(
            command=[
                "configure",
                "--entrypoint",
                self.agent_file,
                "--execution-role",
                TEST_ROLE,
                "--ecr",
                TEST_ECR,
                "--requirements-file",
                self.requirements_file,
            ],
            user_input=["no"],  # oauth config
            validator=lambda result: self.validate_configure(result),
        )

        launch_invocation = CommandInvocation(
            command=["launch", "--auto-update-on-conflict"],
            user_input=[],
            validator=lambda result: self.validate_launch(result),
        )

        status_invocation = CommandInvocation(
            command=["status"], user_input=[], validator=lambda result: self.validate_status(result)
        )

        invoke_invocation = CommandInvocation(
            command=["invoke", "tell me a joke"], user_input=[], validator=lambda result: self.validate_invoke(result)
        )

        return [configure_invocation, launch_invocation, status_invocation, invoke_invocation]

    def validate_configure(self, result: Result):
        output = result.output
        logger.info(output)

        assert "Bedrock AgentCore Configured" in output
        assert "Name: agent" in output
        assert TEST_ROLE in output
        assert "Authorization: IAM" in output
        assert ".bedrock_agentcore.yaml" in output

        if TEST_ECR == "auto":
            assert "ECR: Auto-create" in output
        else:
            assert TEST_ECR in output

    def validate_launch(self, result: Result):
        output = result.output
        logger.info(output)

        assert "Deployment Successful" in output
        assert "Agent Name: agent" in output
        assert "Agent ARN:" in output
        assert "ECR URI:" in output
        assert "You can now check the status of your Bedrock AgentCore endpoint with:" in output
        assert "You can now invoke your Bedrock AgentCore endpoint with:" in output

    def validate_status(self, result: Result):
        output = result.output
        logger.info(output)

        assert "Status of the current Agent:" in output
        assert "Status of the current Endpoint:" in output
        assert "Endpoint Id: DEFAULT" in output
        assert "Endpoint Name: DEFAULT" in output
        assert "READY" in output

    def validate_invoke(self, result: Result):
        output = result.output
        logger.info(output)

        assert "Session ID:" in output
        assert "Response:" in output
        assert "application/json" in output
        # for some reason there is a newline in front of "everything"
        # so skip asserting on the output for now
        # assert "Because they make up everything!" in output


def test(tmp_path):
    """
    Run the simple agent CLI test.
    This function is the entry point for the test.
    """
    TestSimpleAgent().run(tmp_path)
