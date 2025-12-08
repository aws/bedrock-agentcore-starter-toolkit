"""Test policy template utilities."""

import json

import pytest

from bedrock_agentcore_starter_toolkit.utils.runtime.policy_template import (
    render_execution_policy_template,
    render_trust_policy_template,
    validate_rendered_policy,
)


class TestPolicyTemplate:
    """Test policy template rendering."""

    def test_render_trust_policy_template(self):
        """Test rendering trust policy template."""
        region = "us-east-1"
        account_id = "123456789012"

        result = render_trust_policy_template(region, account_id)

        # Validate it's valid JSON
        policy = json.loads(result)

        # Check structure
        assert policy["Version"] == "2012-10-17"
        assert len(policy["Statement"]) == 1

        statement = policy["Statement"][0]
        assert statement["Effect"] == "Allow"
        assert statement["Principal"]["Service"] == "bedrock-agentcore.amazonaws.com"
        assert statement["Action"] == "sts:AssumeRole"

        # Check substitutions
        assert account_id in str(statement["Condition"])
        assert region in str(statement["Condition"])

    def test_render_execution_policy_template(self):
        """Test rendering execution policy template."""
        region = "us-west-2"
        account_id = "123456789012"
        agent_name = "test-agent"

        result = render_execution_policy_template(region, account_id, agent_name)

        # Validate it's valid JSON
        policy = json.loads(result)

        # Check structure
        assert policy["Version"] == "2012-10-17"
        assert len(policy["Statement"]) > 0

        # Check that always-included statements are present
        bedrock_statement = next((s for s in policy["Statement"] if s.get("Sid") == "BedrockModelInvocation"), None)
        assert bedrock_statement is not None
        assert "bedrock:InvokeModel" in bedrock_statement["Action"]

        # Check substitutions
        policy_str = json.dumps(policy)
        assert region in policy_str
        assert account_id in policy_str
        assert agent_name in policy_str

    def test_validate_rendered_policy_valid(self):
        """Test validating valid policy JSON."""
        valid_policy = '{"Version": "2012-10-17", "Statement": []}'

        result = validate_rendered_policy(valid_policy)

        assert isinstance(result, dict)
        assert result["Version"] == "2012-10-17"
        assert result["Statement"] == []

    def test_validate_rendered_policy_invalid(self):
        """Test validating invalid policy JSON."""
        invalid_policy = '{"Version": "2012-10-17", "Statement": [}'  # Missing closing bracket

        with pytest.raises(ValueError, match="Invalid policy JSON"):
            validate_rendered_policy(invalid_policy)

    def test_template_files_exist(self):
        """Test that template files exist in expected location."""
        from bedrock_agentcore_starter_toolkit.utils.runtime.policy_template import _get_template_dir

        template_dir = _get_template_dir()

        trust_template = template_dir / "execution_role_trust_policy.json.j2"
        execution_template = template_dir / "execution_role_policy.json.j2"

        assert trust_template.exists(), f"Trust policy template not found at {trust_template}"
        assert execution_template.exists(), f"Execution policy template not found at {execution_template}"

    def test_policy_has_required_permissions(self):
        """Test that the execution policy contains all required permissions."""
        region = "us-east-1"
        account_id = "123456789012"
        agent_name = "test-agent"

        result = render_execution_policy_template(region, account_id, agent_name)
        policy = json.loads(result)

        # Collect all actions from all statements
        all_actions = []
        for statement in policy["Statement"]:
            actions = statement.get("Action", [])
            if isinstance(actions, str):
                all_actions.append(actions)
            elif isinstance(actions, list):
                all_actions.extend(actions)

        # Check for required permissions from the original policy template
        required_permissions = [
            "logs:DescribeLogStreams",
            "logs:CreateLogGroup",
            "logs:DescribeLogGroups",
            "logs:CreateLogStream",
            "logs:PutLogEvents",
            "xray:PutTraceSegments",
            "xray:PutTelemetryRecords",
            "xray:GetSamplingRules",
            "xray:GetSamplingTargets",
            "cloudwatch:PutMetricData",
            "bedrock:InvokeModel",
            "bedrock:InvokeModelWithResponseStream",
        ]

        for permission in required_permissions:
            assert permission in all_actions, f"Missing required permission: {permission}"

    def test_conditional_ecr_permissions_container(self):
        """Test that ECR permissions are included for container deployments."""
        policy = json.loads(
            render_execution_policy_template(
                region="us-east-1",
                account_id="123456789012",
                agent_name="test-agent",
                deployment_type="container",
            )
        )

        sids = [s.get("Sid") for s in policy["Statement"]]
        assert "ECRImageAccess" in sids
        assert "ECRTokenAccess" in sids

    def test_conditional_ecr_permissions_direct_code(self):
        """Test that ECR permissions are excluded for direct_code_deploy."""
        policy = json.loads(
            render_execution_policy_template(
                region="us-east-1",
                account_id="123456789012",
                agent_name="test-agent",
                deployment_type="direct_code_deploy",
            )
        )

        sids = [s.get("Sid") for s in policy["Statement"]]
        assert "ECRImageAccess" not in sids
        assert "ECRTokenAccess" not in sids

    def test_conditional_ecr_scoped_to_repository(self):
        """Test that ECR permissions are scoped to specific repository when available."""
        policy = json.loads(
            render_execution_policy_template(
                region="us-east-1",
                account_id="123456789012",
                agent_name="test-agent",
                deployment_type="container",
                ecr_repository_name="my-repo",
            )
        )

        ecr_stmt = next((s for s in policy["Statement"] if s.get("Sid") == "ECRImageAccess"), None)
        assert ecr_stmt is not None
        assert len(ecr_stmt["Resource"]) == 1
        assert "my-repo" in ecr_stmt["Resource"][0]
        assert ecr_stmt["Resource"][0] == "arn:aws:ecr:us-east-1:123456789012:repository/my-repo"

    def test_conditional_ecr_wildcard_when_no_repository(self):
        """Test that ECR permissions use wildcard when no specific repository."""
        policy = json.loads(
            render_execution_policy_template(
                region="us-east-1",
                account_id="123456789012",
                agent_name="test-agent",
                deployment_type="container",
                ecr_repository_name=None,
            )
        )

        ecr_stmt = next((s for s in policy["Statement"] if s.get("Sid") == "ECRImageAccess"), None)
        assert ecr_stmt is not None
        assert ecr_stmt["Resource"][0].endswith("repository/*")

    def test_conditional_a2a_runtime_permissions(self):
        """Test that A2A runtime permissions are only included when protocol is A2A."""
        # With A2A protocol
        policy_a2a = json.loads(
            render_execution_policy_template(
                region="us-east-1",
                account_id="123456789012",
                agent_name="test-agent",
                protocol="A2A",
            )
        )
        sids_a2a = [s.get("Sid") for s in policy_a2a["Statement"]]
        assert "BedrockAgentCoreRuntime" in sids_a2a

        # With HTTP protocol
        policy_http = json.loads(
            render_execution_policy_template(
                region="us-east-1",
                account_id="123456789012",
                agent_name="test-agent",
                protocol="HTTP",
            )
        )
        sids_http = [s.get("Sid") for s in policy_http["Statement"]]
        assert "BedrockAgentCoreRuntime" not in sids_http

        # With no protocol
        policy_none = json.loads(
            render_execution_policy_template(
                region="us-east-1",
                account_id="123456789012",
                agent_name="test-agent",
                protocol=None,
            )
        )
        sids_none = [s.get("Sid") for s in policy_none["Statement"]]
        assert "BedrockAgentCoreRuntime" not in sids_none

    def test_conditional_memory_permissions(self):
        """Test that memory permissions are only included when memory is enabled."""
        # With memory enabled (memory_id provided)
        policy_enabled = json.loads(
            render_execution_policy_template(
                region="us-east-1",
                account_id="123456789012",
                agent_name="test-agent",
                memory_id="test-memory-id",
            )
        )
        sids_enabled = [s.get("Sid") for s in policy_enabled["Statement"]]
        assert "BedrockAgentCoreMemory" in sids_enabled

        # With memory disabled (memory_id is None)
        policy_disabled = json.loads(
            render_execution_policy_template(
                region="us-east-1",
                account_id="123456789012",
                agent_name="test-agent",
                memory_id=None,
            )
        )
        sids_disabled = [s.get("Sid") for s in policy_disabled["Statement"]]
        assert "BedrockAgentCoreMemory" not in sids_disabled
        assert "BedrockAgentCoreMemoryCreateMemory" not in sids_disabled

    def test_conditional_memory_scoped_to_memory_id(self):
        """Test that memory permissions are scoped to specific memory ID when available."""
        policy = json.loads(
            render_execution_policy_template(
                region="us-east-1",
                account_id="123456789012",
                agent_name="test-agent",
                memory_id="my-memory-id",
            )
        )

        memory_stmt = next((s for s in policy["Statement"] if s.get("Sid") == "BedrockAgentCoreMemory"), None)
        assert memory_stmt is not None
        assert len(memory_stmt["Resource"]) == 1
        assert "my-memory-id" in memory_stmt["Resource"][0]
        assert memory_stmt["Resource"][0] == "arn:aws:bedrock-agentcore:us-east-1:123456789012:memory/my-memory-id"

        # CreateMemory permission should NOT be included when memory_id is provided
        sids = [s.get("Sid") for s in policy["Statement"]]
        assert "BedrockAgentCoreMemoryCreateMemory" not in sids

    def test_code_interpreter_always_included(self):
        """Test that CodeInterpreter permissions are always included and scoped to AWS managed."""
        policy = json.loads(
            render_execution_policy_template(
                region="us-west-2",
                account_id="123456789012",
                agent_name="test-agent",
            )
        )

        ci_stmt = next((s for s in policy["Statement"] if s.get("Sid") == "BedrockAgentCoreCodeInterpreter"), None)
        assert ci_stmt is not None
        assert len(ci_stmt["Resource"]) == 1
        # Should be scoped to AWS managed code interpreter only
        assert (
            ci_stmt["Resource"][0] == "arn:aws:bedrock-agentcore:us-west-2:aws:code-interpreter/aws.codeinterpreter.v1"
        )

    def test_all_combinations_valid_json(self):
        """Test that all combinations of parameters produce valid JSON."""
        test_cases = [
            # Container + A2A + Memory + ECR repo + Memory ID
            {
                "deployment_type": "container",
                "protocol": "A2A",
                "memory_id": "mem-123",
                "ecr_repository_name": "my-repo",
            },
            # Direct code + HTTP + No memory
            {"deployment_type": "direct_code_deploy", "protocol": "HTTP", "memory_id": None},
            # Container + MCP + No memory
            {"deployment_type": "container", "protocol": "MCP", "memory_id": None},
            # Direct code + No protocol + Memory with ID
            {
                "deployment_type": "direct_code_deploy",
                "protocol": None,
                "memory_id": "mem-456",
            },
        ]

        for params in test_cases:
            result = render_execution_policy_template(
                region="us-east-1", account_id="123456789012", agent_name="test-agent", **params
            )
            # Should not raise any exceptions
            policy = json.loads(result)
            assert policy["Version"] == "2012-10-17"
            assert isinstance(policy["Statement"], list)
            assert len(policy["Statement"]) > 0

    def test_defaults_are_secure(self):
        """Test that default parameters result in minimal permissions (secure by default)."""
        policy = json.loads(
            render_execution_policy_template(region="us-east-1", account_id="123456789012", agent_name="test-agent")
        )

        sids = [s.get("Sid") for s in policy["Statement"]]

        # Should NOT include these by default (secure by default)
        assert "ECRImageAccess" not in sids  # No container deployment
        assert "ECRTokenAccess" not in sids  # No container deployment
        assert "BedrockAgentCoreRuntime" not in sids  # No A2A protocol
        assert "BedrockAgentCoreMemory" not in sids  # No memory enabled

        # Should always include these
        assert "BedrockModelInvocation" in sids
        assert "BedrockAgentCoreCodeInterpreter" in sids
        assert "BedrockAgentCoreIdentity" in sids
