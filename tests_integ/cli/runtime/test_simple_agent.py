import json
import logging
import textwrap
from typing import List

import boto3
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
        # Extract role name from ARN if provided
        if TEST_ROLE:
            self.role_name = TEST_ROLE.split("/")[-1]
        else:
            self.role_name = None

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
                    return agent(payload.get("prompt"))

                app.run()
            """).strip()
            file.write(content)

        with open(self.requirements_file, "w") as file:
            content = textwrap.dedent("""
                strands-agents
                bedrock-agentcore
            """).strip()
            file.write(content)

    def _setup_role_trust_policy(self):
        """
        Ensure the IAM role has the required trust relationship with Bedrock.
        """
        try:
            iam_client = boto3.client("iam")

            # Get current trust policy
            response = iam_client.get_role(RoleName=self.role_name)
            current_policy = response["Role"]["AssumeRolePolicyDocument"]

            # Check if bedrock is already a trusted service
            bedrock_trusted = False
            for statement in current_policy.get("Statement", []):
                principal = statement.get("Principal", {})
                service = principal.get("Service", [])
                if isinstance(service, str):
                    service = [service]
                if "bedrock.amazonaws.com" in service:
                    bedrock_trusted = True
                    break

            # Add bedrock trust if needed
            if not bedrock_trusted:
                logger.info("Adding bedrock.amazonaws.com to trust policy for role %s", self.role_name)

                # Copy the existing policy and add bedrock
                if len(current_policy.get("Statement", [])) > 0:
                    # Add to existing policy
                    new_statement = {
                        "Effect": "Allow",
                        "Principal": {"Service": "bedrock.amazonaws.com"},
                        "Action": "sts:AssumeRole",
                    }
                    current_policy["Statement"].append(new_statement)
                else:
                    # Create new policy
                    current_policy = {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Principal": {"Service": "bedrock.amazonaws.com"},
                                "Action": "sts:AssumeRole",
                            }
                        ],
                    }

                # Update the role
                iam_client.update_assume_role_policy(RoleName=self.role_name, PolicyDocument=json.dumps(current_policy))
                logger.info("Updated trust policy for role %s", self.role_name)
            else:
                logger.info("Role %s already trusts bedrock.amazonaws.com", self.role_name)

        except Exception as e:
            logger.error("Error updating role trust policy: %s", str(e))
            raise

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
                "--deployment-type",
                "container",
                "--non-interactive",
            ],
            user_input=[],
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
            command=["invoke", '{"prompt": "tell me a joke"}'],
            user_input=[],
            validator=lambda result: self.validate_invoke(result),
        )

        return [configure_invocation, launch_invocation, status_invocation, invoke_invocation]

    def validate_configure(self, result: Result):
        output = result.output
        logger.info(output)

        assert "Configuration Success" in output
        assert "Agent Name: agent" in output

        # Handle both explicit role and auto-create
        if TEST_ROLE:
            assert TEST_ROLE in output
        else:
            assert "Auto-create" in output or "Execution Role:" in output

        assert "Authorization: IAM" in output
        assert ".bedrock_agentcore.yaml" in output

        if TEST_ECR == "auto":
            assert "ECR Repository: Auto-create" in output
        else:
            assert TEST_ECR in output

    def validate_launch(self, result: Result):
        output = result.output
        logger.info(output)

        assert "Deployment Success" in output
        assert "Agent Name: agent" in output
        assert "Agent ARN:" in output
        assert "ECR URI:" in output
        assert "Next Steps:" in output
        assert "agentcore status" in output
        assert "agentcore invoke" in output

    def validate_status(self, result: Result):
        output = result.output
        logger.info(output)

        assert "Agent Details:" in output
        assert "Agent Name: agent" in output
        assert "Agent ARN:" in output
        assert "Endpoint: DEFAULT" in output
        assert "READY" in output

    def validate_invoke(self, result: Result):
        output = result.output
        logger.info(output)

        # Validate new consistent panel format
        assert "Session:" in output
        assert "Request ID:" in output
        assert "ARN:" in output
        assert "Logs:" in output
        assert "Response:" in output


def test(tmp_path):
    """
    Run the simple agent CLI test.
    This function is the entry point for the test.
    """
    TestSimpleAgent().run(tmp_path)
