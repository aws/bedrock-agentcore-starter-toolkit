"""Tests for Bedrock AgentCore Policy CLI commands."""

import json
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from bedrock_agentcore_starter_toolkit.cli.policy.commands import policy_app

runner = CliRunner()


@pytest.fixture
def mock_policy_client():
    """Fixture to create a mocked PolicyClient."""
    with (
        patch("bedrock_agentcore_starter_toolkit.cli.policy.commands.PolicyClient") as mock_client_class,
        patch("bedrock_agentcore_starter_toolkit.cli.common.ensure_valid_aws_creds", return_value=(True, None)),
    ):
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        yield mock_client


# ==================== Policy Engine Command Tests ====================


def test_create_policy_engine_basic(mock_policy_client):
    """Test basic create-policy-engine command."""
    mock_response = {
        "policyEngineId": "testEngine-123",
        "policyEngineArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy-engine/testEngine-123",
        "status": "CREATING",
        "name": "TestEngine",
    }
    mock_policy_client.create_policy_engine.return_value = mock_response

    result = runner.invoke(
        policy_app,
        [
            "create-policy-engine",
            "--name",
            "TestEngine",
            "--region",
            "us-east-1",
            "--description",
            "Test policy engine",
        ],
    )

    assert result.exit_code == 0
    assert "Policy engine creation initiated" in result.output
    assert "testEngine-123" in result.output
    mock_policy_client.create_policy_engine.assert_called_once_with(name="TestEngine", description="Test policy engine")


def test_create_policy_engine_defaults(mock_policy_client):
    """Test create-policy-engine with default values."""
    mock_policy_client.create_policy_engine.return_value = {"policyEngineId": "default-engine"}

    result = runner.invoke(policy_app, ["create-policy-engine", "--name", "DefaultEngine"])

    assert result.exit_code == 0
    assert "Policy engine creation initiated" in result.output


def test_get_policy_engine(mock_policy_client):
    """Test get-policy-engine command."""
    mock_policy_client.get_policy_engine.return_value = {
        "policyEngineId": "engine-123",
        "name": "TestEngine",
        "status": "ACTIVE",
        "description": "Test description",
    }

    result = runner.invoke(policy_app, ["get-policy-engine", "--policy-engine-id", "engine-123"])

    assert result.exit_code == 0
    assert "Policy Engine Details" in result.output
    assert "engine-123" in result.output
    assert "TestEngine" in result.output
    mock_policy_client.get_policy_engine.assert_called_once_with("engine-123")


def test_update_policy_engine(mock_policy_client):
    """Test update-policy-engine command."""
    mock_policy_client.update_policy_engine.return_value = {
        "policyEngineId": "engine-123",
        "status": "UPDATING",
        "updatedAt": "2024-01-15T10:30:00Z",
    }

    result = runner.invoke(
        policy_app,
        ["update-policy-engine", "--policy-engine-id", "engine-123", "--description", "Updated description"],
    )

    assert result.exit_code == 0
    assert "Policy engine update initiated" in result.output
    assert "2024-01-15T10:30:00Z" in result.output  # Verify updatedAt is displayed
    mock_policy_client.update_policy_engine.assert_called_once_with(
        policy_engine_id="engine-123", description="Updated description"
    )


def test_list_policy_engines(mock_policy_client):
    """Test list-policy-engines command."""
    mock_policy_client.list_policy_engines.return_value = {
        "policyEngines": [
            {"policyEngineId": "engine-1", "name": "Engine1", "status": "ACTIVE", "createdAt": "2024-01-01"},
            {"policyEngineId": "engine-2", "name": "Engine2", "status": "ACTIVE", "createdAt": "2024-01-02"},
        ]
    }

    result = runner.invoke(policy_app, ["list-policy-engines", "--max-results", "10"])

    assert result.exit_code == 0
    assert "Policy Engines" in result.output
    assert "engine-1" in result.output
    assert "engine-2" in result.output
    mock_policy_client.list_policy_engines.assert_called_once_with(max_results=10, next_token=None)


def test_list_policy_engines_empty(mock_policy_client):
    """Test list-policy-engines with no results."""
    mock_policy_client.list_policy_engines.return_value = {"policyEngines": []}

    result = runner.invoke(policy_app, ["list-policy-engines"])

    assert result.exit_code == 0
    assert "No policy engines found" in result.output


def test_list_policy_engines_with_pagination(mock_policy_client):
    """Test list-policy-engines with pagination token."""
    mock_policy_client.list_policy_engines.return_value = {
        "policyEngines": [{"policyEngineId": "engine-1", "name": "Engine1", "status": "ACTIVE"}],
        "nextToken": "next-page-token",
    }

    result = runner.invoke(policy_app, ["list-policy-engines", "--next-token", "token123"])

    assert result.exit_code == 0
    assert "next-page-token" in result.output
    mock_policy_client.list_policy_engines.assert_called_once_with(max_results=None, next_token="token123")


def test_delete_policy_engine(mock_policy_client):
    """Test delete-policy-engine command."""
    mock_policy_client.delete_policy_engine.return_value = {"status": "DELETING"}

    result = runner.invoke(policy_app, ["delete-policy-engine", "--policy-engine-id", "engine-123"])

    assert result.exit_code == 0
    assert "Policy engine deletion initiated" in result.output
    assert "engine-123" in result.output
    mock_policy_client.delete_policy_engine.assert_called_once_with("engine-123")


def test_policy_engine_api_error(mock_policy_client):
    """Test error handling when API call fails."""
    mock_policy_client.get_policy_engine.side_effect = Exception("API Error")

    result = runner.invoke(policy_app, ["get-policy-engine", "--policy-engine-id", "engine-123"])

    # Command should fail but not crash
    assert result.exit_code != 0


# ==================== Policy Command Tests ====================


def test_create_policy_basic(mock_policy_client):
    """Test basic create-policy command."""
    mock_response = {
        "policyId": "policy-123",
        "policyArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy/policy-123",
        "status": "CREATING",
        "name": "TestPolicy",
    }
    mock_policy_client.create_policy.return_value = mock_response

    definition = {"cedar": {"statement": "permit(principal, action, resource);"}}

    result = runner.invoke(
        policy_app,
        [
            "create-policy",
            "--policy-engine-id",
            "engine-123",
            "--name",
            "TestPolicy",
            "--definition",
            json.dumps(definition),
        ],
    )

    assert result.exit_code == 0
    assert "Policy creation initiated" in result.output
    assert "policy-123" in result.output
    call_args = mock_policy_client.create_policy.call_args[1]
    assert call_args["policy_engine_id"] == "engine-123"
    assert call_args["name"] == "TestPolicy"
    assert call_args["definition"] == definition


def test_create_policy_with_validation_mode(mock_policy_client):
    """Test create-policy with validation mode."""
    mock_policy_client.create_policy.return_value = {"policyId": "policy-123", "status": "CREATING"}

    definition = {"cedar": {"statement": "permit(principal, action, resource);"}}

    result = runner.invoke(
        policy_app,
        [
            "create-policy",
            "--policy-engine-id",
            "engine-123",
            "--name",
            "TestPolicy",
            "--definition",
            json.dumps(definition),
            "--validation-mode",
            "FAIL_ON_ANY_FINDINGS",
        ],
    )

    assert result.exit_code == 0
    call_args = mock_policy_client.create_policy.call_args[1]
    assert call_args["validation_mode"] == "FAIL_ON_ANY_FINDINGS"


def test_create_policy_with_description(mock_policy_client):
    """Test create-policy with description."""
    mock_policy_client.create_policy.return_value = {"policyId": "policy-123"}

    definition = {"cedar": {"statement": "permit(principal, action, resource);"}}

    result = runner.invoke(
        policy_app,
        [
            "create-policy",
            "--policy-engine-id",
            "engine-123",
            "--name",
            "TestPolicy",
            "--definition",
            json.dumps(definition),
            "--description",
            "Test policy description",
        ],
    )

    assert result.exit_code == 0
    call_args = mock_policy_client.create_policy.call_args[1]
    assert call_args["description"] == "Test policy description"


def test_create_policy_invalid_json(mock_policy_client):
    """Test create-policy with invalid JSON definition."""
    result = runner.invoke(
        policy_app,
        [
            "create-policy",
            "--policy-engine-id",
            "engine-123",
            "--name",
            "TestPolicy",
            "--definition",
            "invalid-json",
        ],
    )

    assert result.exit_code == 1
    assert "Error parsing definition JSON" in result.output


def test_get_policy(mock_policy_client):
    """Test get-policy command."""
    mock_policy_client.get_policy.return_value = {
        "policyId": "policy-123",
        "name": "TestPolicy",
        "status": "ACTIVE",
        "policyArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy/policy-123",
        "definition": {"cedar": {"statement": "permit(principal, action, resource);"}},
    }

    result = runner.invoke(policy_app, ["get-policy", "--policy-engine-id", "engine-123", "--policy-id", "policy-123"])

    assert result.exit_code == 0
    assert "Policy Details" in result.output
    assert "policy-123" in result.output
    assert "arn:aws:bedrock-agentcore:us-east-1:123:policy/policy-123" in result.output
    mock_policy_client.get_policy.assert_called_once_with("engine-123", "policy-123")


def test_update_policy(mock_policy_client):
    """Test update-policy command."""
    mock_policy_client.update_policy.return_value = {"policyId": "policy-123", "status": "UPDATING"}

    definition = {"cedar": {"statement": "permit(principal, action, resource) when { true };"}}

    result = runner.invoke(
        policy_app,
        [
            "update-policy",
            "--policy-engine-id",
            "engine-123",
            "--policy-id",
            "policy-123",
            "--definition",
            json.dumps(definition),
        ],
    )

    assert result.exit_code == 0
    assert "Policy update initiated" in result.output
    call_args = mock_policy_client.update_policy.call_args[1]
    assert call_args["definition"] == definition


def test_update_policy_invalid_json(mock_policy_client):
    """Test update-policy with invalid JSON."""
    result = runner.invoke(
        policy_app,
        [
            "update-policy",
            "--policy-engine-id",
            "engine-123",
            "--policy-id",
            "policy-123",
            "--definition",
            "bad-json",
        ],
    )

    assert result.exit_code == 1
    assert "Error parsing definition JSON" in result.output


def test_list_policies(mock_policy_client):
    """Test list-policies command."""
    mock_policy_client.list_policies.return_value = {
        "policies": [
            {"policyId": "p1", "name": "Policy1", "status": "ACTIVE", "createdAt": "2024-01-01"},
            {"policyId": "p2", "name": "Policy2", "status": "ACTIVE", "createdAt": "2024-01-02"},
        ]
    }

    result = runner.invoke(policy_app, ["list-policies", "--policy-engine-id", "engine-123"])

    assert result.exit_code == 0
    assert "Policies" in result.output
    assert "p1" in result.output
    assert "p2" in result.output


def test_list_policies_empty(mock_policy_client):
    """Test list-policies with no results."""
    mock_policy_client.list_policies.return_value = {"policies": []}

    result = runner.invoke(policy_app, ["list-policies", "--policy-engine-id", "engine-123"])

    assert result.exit_code == 0
    assert "No policies found" in result.output


def test_list_policies_with_resource_scope(mock_policy_client):
    """Test list-policies with resource scope filter."""
    mock_policy_client.list_policies.return_value = {"policies": []}

    resource_arn = "arn:aws:bedrock-agentcore:us-east-1:123:gateway/my-gateway"
    result = runner.invoke(
        policy_app,
        ["list-policies", "--policy-engine-id", "engine-123", "--target-resource-scope", resource_arn],
    )

    assert result.exit_code == 0
    call_args = mock_policy_client.list_policies.call_args[1]
    assert call_args["target_resource_scope"] == resource_arn


def test_list_policies_with_pagination(mock_policy_client):
    """Test list-policies with pagination parameters."""
    mock_policy_client.list_policies.return_value = {
        "policies": [{"policyId": "p1", "name": "Policy1", "status": "ACTIVE"}],
        "nextToken": "next-page",
    }

    result = runner.invoke(
        policy_app,
        ["list-policies", "--policy-engine-id", "engine-123", "--max-results", "5", "--next-token", "token123"],
    )

    assert result.exit_code == 0
    assert "next-page" in result.output
    call_args = mock_policy_client.list_policies.call_args[1]
    assert call_args["max_results"] == 5
    assert call_args["next_token"] == "token123"


def test_delete_policy(mock_policy_client):
    """Test delete-policy command."""
    mock_policy_client.delete_policy.return_value = {"status": "DELETING"}

    result = runner.invoke(
        policy_app,
        ["delete-policy", "--policy-engine-id", "engine-123", "--policy-id", "policy-123"],
    )

    assert result.exit_code == 0
    assert "Policy deletion initiated" in result.output
    assert "policy-123" in result.output
    mock_policy_client.delete_policy.assert_called_once_with("engine-123", "policy-123")


def test_policy_api_error(mock_policy_client):
    """Test error handling when policy API call fails."""
    mock_policy_client.get_policy.side_effect = Exception("API Error")

    result = runner.invoke(policy_app, ["get-policy", "--policy-engine-id", "engine-123", "--policy-id", "policy-123"])

    assert result.exit_code != 0


# ==================== Policy Generation Command Tests ====================


def test_start_policy_generation(mock_policy_client):
    """Test start-policy-generation command."""
    mock_response = {
        "policyGenerationId": "gen-123",
        "policyGenerationArn": "arn:aws:bedrock-agentcore:us-east-1:123:generation/gen-123",
        "status": "IN_PROGRESS",
        "name": "test-generation",
    }
    mock_policy_client.start_policy_generation.return_value = mock_response

    result = runner.invoke(
        policy_app,
        [
            "start-policy-generation",
            "--policy-engine-id",
            "engine-123",
            "--name",
            "test-generation",
            "--resource-arn",
            "arn:aws:bedrock-agentcore:us-east-1:123:gateway/my-gateway",
            "--content",
            "Allow refunds under $1000",
        ],
    )

    assert result.exit_code == 0
    assert "Policy generation initiated" in result.output
    assert "gen-123" in result.output
    call_args = mock_policy_client.start_policy_generation.call_args[1]
    assert call_args["policy_engine_id"] == "engine-123"
    assert call_args["name"] == "test-generation"
    assert call_args["resource"]["arn"] == "arn:aws:bedrock-agentcore:us-east-1:123:gateway/my-gateway"
    assert call_args["content"]["rawText"] == "Allow refunds under $1000"


def test_start_policy_generation_with_region(mock_policy_client):
    """Test start-policy-generation with custom region."""
    mock_policy_client.start_policy_generation.return_value = {
        "policyGenerationId": "gen-123",
        "status": "IN_PROGRESS",
    }

    result = runner.invoke(
        policy_app,
        [
            "start-policy-generation",
            "--policy-engine-id",
            "engine-123",
            "--name",
            "test-gen",
            "--resource-arn",
            "arn:aws:bedrock-agentcore:us-west-2:123:gateway/gw",
            "--content",
            "Allow all actions",
            "--region",
            "us-west-2",
        ],
    )

    assert result.exit_code == 0


def test_get_policy_generation(mock_policy_client):
    """Test get-policy-generation command."""
    mock_policy_client.get_policy_generation.return_value = {
        "policyGenerationId": "gen-123",
        "name": "test-generation",
        "status": "COMPLETED",
    }

    result = runner.invoke(
        policy_app, ["get-policy-generation", "--policy-engine-id", "engine-123", "--generation-id", "gen-123"]
    )

    assert result.exit_code == 0
    assert "Policy Generation Details" in result.output
    assert "gen-123" in result.output
    mock_policy_client.get_policy_generation.assert_called_once_with("engine-123", "gen-123")


def test_list_policy_generation_assets(mock_policy_client):
    """Test list-policy-generation-assets command."""
    mock_response = {
        "policyGenerationAssets": [
            {"assetId": "asset-1", "type": "POLICY", "status": "CREATED"},
            {"assetId": "asset-2", "type": "POLICY", "status": "CREATED"},
        ],
        "ResponseMetadata": {"RequestId": "test-request-id"},
    }
    mock_policy_client.list_policy_generation_assets.return_value = mock_response

    result = runner.invoke(
        policy_app, ["list-policy-generation-assets", "--policy-engine-id", "engine-123", "--generation-id", "gen-123"]
    )

    assert result.exit_code == 0
    # Verify JSON output contains filtered response (no ResponseMetadata)
    output_json = json.loads(result.output)
    assert "ResponseMetadata" not in output_json
    assert "policyGenerationAssets" in output_json
    assert len(output_json["policyGenerationAssets"]) == 2
    mock_policy_client.list_policy_generation_assets.assert_called_once_with("engine-123", "gen-123", None, None)


def test_list_policy_generation_assets_empty(mock_policy_client):
    """Test list-policy-generation-assets with no results."""
    mock_response = {"policyGenerationAssets": [], "ResponseMetadata": {"RequestId": "test-request-id"}}
    mock_policy_client.list_policy_generation_assets.return_value = mock_response

    result = runner.invoke(
        policy_app, ["list-policy-generation-assets", "--policy-engine-id", "engine-123", "--generation-id", "gen-123"]
    )

    assert result.exit_code == 0
    # Verify JSON output (filtered, no ResponseMetadata)
    output_json = json.loads(result.output)
    assert "ResponseMetadata" not in output_json
    assert len(output_json["policyGenerationAssets"]) == 0


def test_list_policy_generation_assets_with_pagination(mock_policy_client):
    """Test list-policy-generation-assets with pagination."""
    mock_response = {
        "policyGenerationAssets": [{"assetId": "asset-1", "type": "POLICY", "status": "CREATED"}],
        "nextToken": "next-token",
        "ResponseMetadata": {"RequestId": "test-request-id"},
    }
    mock_policy_client.list_policy_generation_assets.return_value = mock_response

    result = runner.invoke(
        policy_app,
        [
            "list-policy-generation-assets",
            "--policy-engine-id",
            "engine-123",
            "--generation-id",
            "gen-123",
            "--max-results",
            "10",
        ],
    )

    assert result.exit_code == 0
    # Verify JSON output includes nextToken but not ResponseMetadata
    output_json = json.loads(result.output)
    assert "ResponseMetadata" not in output_json
    assert output_json["nextToken"] == "next-token"
    assert len(output_json["policyGenerationAssets"]) == 1
    mock_policy_client.list_policy_generation_assets.assert_called_once_with("engine-123", "gen-123", 10, None)


def test_list_policy_generations(mock_policy_client):
    """Test list-policy-generations command."""
    mock_policy_client.list_policy_generations.return_value = {
        "policyGenerations": [
            {"policyGenerationId": "gen-1", "name": "Gen1", "status": "COMPLETED", "createdAt": "2024-01-01"},
            {"policyGenerationId": "gen-2", "name": "Gen2", "status": "IN_PROGRESS", "createdAt": "2024-01-02"},
        ]
    }

    result = runner.invoke(policy_app, ["list-policy-generations", "--policy-engine-id", "engine-123"])

    assert result.exit_code == 0
    assert "Policy Generations" in result.output
    assert "gen-1" in result.output
    assert "gen-2" in result.output


def test_list_policy_generations_empty(mock_policy_client):
    """Test list-policy-generations with no results."""
    mock_policy_client.list_policy_generations.return_value = {"policyGenerations": []}

    result = runner.invoke(policy_app, ["list-policy-generations", "--policy-engine-id", "engine-123"])

    assert result.exit_code == 0
    assert "No policy generations found" in result.output


def test_list_policy_generations_with_pagination(mock_policy_client):
    """Test list-policy-generations with pagination parameters."""
    mock_policy_client.list_policy_generations.return_value = {
        "policyGenerations": [{"policyGenerationId": "gen-1", "name": "Gen1", "status": "COMPLETED"}],
        "nextToken": "next-page",
    }

    result = runner.invoke(
        policy_app,
        [
            "list-policy-generations",
            "--policy-engine-id",
            "engine-123",
            "--max-results",
            "5",
            "--next-token",
            "token123",
        ],
    )

    assert result.exit_code == 0
    assert "next-page" in result.output
    call_args = mock_policy_client.list_policy_generations.call_args[1]
    assert call_args["max_results"] == 5
    assert call_args["next_token"] == "token123"


def test_policy_generation_api_error(mock_policy_client):
    """Test error handling when generation API call fails."""
    mock_policy_client.get_policy_generation.side_effect = Exception("API Error")

    result = runner.invoke(
        policy_app, ["get-policy-generation", "--policy-engine-id", "engine-123", "--generation-id", "gen-123"]
    )

    assert result.exit_code != 0


# ==================== Tests for Optional Field Display ====================


def test_create_policy_engine_with_all_optional_fields(mock_policy_client):
    """Test create-policy-engine displays all optional fields."""
    mock_response = {
        "policyEngineId": "testEngine-123",
        "policyEngineArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy-engine/testEngine-123",
        "status": "CREATING",
        "name": "TestEngine",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
    }
    mock_policy_client.create_policy_engine.return_value = mock_response

    result = runner.invoke(policy_app, ["create-policy-engine", "--name", "TestEngine"])

    assert result.exit_code == 0
    assert "arn:aws:bedrock-agentcore:us-east-1:123:policy-engine/testEngine-123" in result.output


def test_get_policy_engine_with_all_timestamps(mock_policy_client):
    """Test get-policy-engine displays all timestamp fields."""
    mock_policy_client.get_policy_engine.return_value = {
        "policyEngineId": "engine-123",
        "name": "TestEngine",
        "status": "ACTIVE",
        "description": "Test description",
        "policyEngineArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy-engine/engine-123",
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-02T00:00:00Z",
    }

    result = runner.invoke(policy_app, ["get-policy-engine", "--policy-engine-id", "engine-123"])

    assert result.exit_code == 0
    assert "2024-01-01T00:00:00Z" in result.output
    assert "2024-01-02T00:00:00Z" in result.output


def test_create_policy_with_arn(mock_policy_client):
    """Test create-policy displays ARN when present."""
    mock_response = {
        "policyId": "policy-123",
        "policyArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy/policy-123",
        "status": "CREATING",
        "name": "TestPolicy",
    }
    mock_policy_client.create_policy.return_value = mock_response

    definition = {"cedar": {"statement": "permit(principal, action, resource);"}}

    result = runner.invoke(
        policy_app,
        [
            "create-policy",
            "--policy-engine-id",
            "engine-123",
            "--name",
            "TestPolicy",
            "--definition",
            json.dumps(definition),
        ],
    )

    assert result.exit_code == 0
    assert "arn:aws:bedrock-agentcore:us-east-1:123:policy/policy-123" in result.output


def test_update_policy_with_updated_at(mock_policy_client):
    """Test update-policy displays updatedAt when present."""
    mock_policy_client.update_policy.return_value = {
        "policyId": "policy-123",
        "status": "UPDATING",
        "updatedAt": "2024-01-02T00:00:00Z",
    }

    definition = {"cedar": {"statement": "permit(principal, action, resource);"}}

    result = runner.invoke(
        policy_app,
        [
            "update-policy",
            "--policy-engine-id",
            "engine-123",
            "--policy-id",
            "policy-123",
            "--definition",
            json.dumps(definition),
        ],
    )

    assert result.exit_code == 0
    assert "2024-01-02T00:00:00Z" in result.output


def test_list_policy_generation_assets_with_data(mock_policy_client):
    """Test list-policy-generation-assets displays JSON correctly."""
    mock_response = {
        "policyGenerationAssets": [
            {"assetId": "asset-1", "type": "POLICY", "status": "CREATED"},
            {"assetId": "asset-2", "type": "SCHEMA", "status": "CREATED"},
        ],
        "ResponseMetadata": {"RequestId": "test-request-id"},
    }
    mock_policy_client.list_policy_generation_assets.return_value = mock_response

    result = runner.invoke(
        policy_app, ["list-policy-generation-assets", "--policy-engine-id", "engine-123", "--generation-id", "gen-123"]
    )

    assert result.exit_code == 0
    # Verify JSON output structure (filtered, no ResponseMetadata)
    output_json = json.loads(result.output)
    assert "ResponseMetadata" not in output_json
    assert output_json["policyGenerationAssets"][0]["assetId"] == "asset-1"
    assert output_json["policyGenerationAssets"][0]["type"] == "POLICY"
    assert output_json["policyGenerationAssets"][1]["assetId"] == "asset-2"
    assert output_json["policyGenerationAssets"][1]["type"] == "SCHEMA"


# ==================== Region Option Consistency Tests ====================


def test_all_commands_accept_region_option(mock_policy_client):
    """Test that all commands accept --region option."""
    # Mock return values
    mock_policy_client.create_policy_engine.return_value = {"policyEngineId": "engine-123"}
    mock_policy_client.get_policy_engine.return_value = {"policyEngineId": "engine-123"}
    mock_policy_client.list_policy_engines.return_value = {"policyEngines": []}
    mock_policy_client.delete_policy_engine.return_value = {}
    mock_policy_client.create_policy.return_value = {"policyId": "policy-123"}
    mock_policy_client.get_policy.return_value = {"policyId": "policy-123"}
    mock_policy_client.list_policies.return_value = {"policies": []}
    mock_policy_client.delete_policy.return_value = {}
    mock_policy_client.start_policy_generation.return_value = {"policyGenerationId": "gen-123"}
    mock_policy_client.get_policy_generation.return_value = {"policyGenerationId": "gen-123"}
    mock_policy_client.list_policy_generations.return_value = {"policyGenerations": []}
    mock_policy_client.list_policy_generation_assets.return_value = {"policyGenerationAssets": []}

    definition = json.dumps({"cedar": {"statement": "permit(principal, action, resource);"}})

    commands_with_region = [
        (["create-policy-engine", "--name", "test", "--region", "us-west-2"]),
        (["get-policy-engine", "--policy-engine-id", "e1", "--region", "us-west-2"]),
        (["list-policy-engines", "--region", "us-west-2"]),
        (["delete-policy-engine", "--policy-engine-id", "e1", "--region", "us-west-2"]),
        (
            [
                "create-policy",
                "--policy-engine-id",
                "e1",
                "--name",
                "p1",
                "--definition",
                definition,
                "--region",
                "us-west-2",
            ]
        ),
        (["get-policy", "--policy-engine-id", "e1", "--policy-id", "p1", "--region", "us-west-2"]),
        (["list-policies", "--policy-engine-id", "e1", "--region", "us-west-2"]),
        (["delete-policy", "--policy-engine-id", "e1", "--policy-id", "p1", "--region", "us-west-2"]),
        (
            [
                "start-policy-generation",
                "--policy-engine-id",
                "e1",
                "--name",
                "g1",
                "--resource-arn",
                "arn:aws:test",
                "--content",
                "test",
                "--region",
                "us-west-2",
            ]
        ),
        (
            [
                "get-policy-generation",
                "--policy-engine-id",
                "e1",
                "--generation-id",
                "g1",
                "--region",
                "us-west-2",
            ]
        ),
        (["list-policy-generations", "--policy-engine-id", "e1", "--region", "us-west-2"]),
        (
            [
                "list-policy-generation-assets",
                "--policy-engine-id",
                "e1",
                "--generation-id",
                "g1",
                "--region",
                "us-west-2",
            ]
        ),
    ]

    for command_args in commands_with_region:
        result = runner.invoke(policy_app, command_args)
        # Should not fail due to region option
        assert result.exit_code == 0 or result.exit_code == 1  # 1 is acceptable for controlled errors
