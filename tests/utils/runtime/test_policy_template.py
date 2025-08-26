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

        # Find specific statements
        ecr_statement = next((s for s in policy["Statement"] if s.get("Sid") == "ECRImageAccess"), None)
        assert ecr_statement is not None
        assert "ecr:BatchGetImage" in ecr_statement["Action"]

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
            "ecr:BatchGetImage",
            "ecr:GetDownloadUrlForLayer",
            "ecr:GetAuthorizationToken",
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
            "bedrock-agentcore:GetWorkloadAccessToken",
            "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
            "bedrock-agentcore:GetWorkloadAccessTokenForUserId",
            "bedrock:InvokeModel",
            "bedrock:InvokeModelWithResponseStream",
        ]

        for permission in required_permissions:
            assert permission in all_actions, f"Missing required permission: {permission}"
