"""Tests for Bedrock AgentCore Policy Client operations."""

from unittest.mock import Mock, patch

import pytest

from bedrock_agentcore_starter_toolkit.operations.policy import PolicyClient
from bedrock_agentcore_starter_toolkit.operations.policy.exceptions import (
    PolicyEngineNotFoundException,
    PolicyGenerationNotFoundException,
    PolicyNotFoundException,
    PolicySetupException,
)

# Add timeout marker for all tests in this module
pytestmark = pytest.mark.timeout(10)  # 10 second timeout per test


@pytest.fixture
def mock_boto_client():
    """Mock boto3 client."""
    with patch("boto3.client") as mock:
        yield mock


@pytest.fixture
def mock_session():
    """Mock boto3 session."""
    with patch("boto3.Session") as mock:
        yield mock


@pytest.fixture
def policy_client(mock_boto_client, mock_session):
    """Create PolicyClient instance with mocked dependencies."""
    return PolicyClient(region_name="us-east-1")


class TestPolicyClientInit:
    """Test PolicyClient initialization."""

    def test_client_init_with_default_region(self, mock_boto_client, mock_session):
        """Test client initialization with default region."""
        client = PolicyClient()

        mock_boto_client.assert_called_with("bedrock-agentcore-control", region_name="us-west-2")
        assert client.region == "us-west-2"

    def test_client_init_with_custom_region(self, mock_boto_client, mock_session):
        """Test client initialization with custom region."""
        client = PolicyClient(region_name="us-west-2")

        mock_boto_client.assert_called_with("bedrock-agentcore-control", region_name="us-west-2")
        assert client.region == "us-west-2"


class TestPolicyEngineOperations:
    """Test policy engine CRUD operations."""

    def test_create_policy_engine_success(self, policy_client):
        """Test successful policy engine creation."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_response = {
            "policyEngineId": "engine-123",
            "policyEngineArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy-engine/engine-123",
            "status": "CREATING",
        }
        mock_client.create_policy_engine.return_value = mock_response

        result = policy_client.create_policy_engine(name="TestEngine", description="Test description")

        assert result == mock_response
        mock_client.create_policy_engine.assert_called_once_with(name="TestEngine", description="Test description")

    def test_create_policy_engine_with_client_token(self, policy_client):
        """Test create policy engine with client token."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_response = {
            "policyEngineId": "engine-123",
            "policyEngineArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy-engine/engine-123",
            "status": "CREATING",
        }
        mock_client.create_policy_engine.return_value = mock_response

        result = policy_client.create_policy_engine(
            name="TestEngine", description="Test description", client_token="my-token-123"
        )

        assert result == mock_response
        mock_client.create_policy_engine.assert_called_once_with(
            name="TestEngine", description="Test description", clientToken="my-token-123"
        )

    def test_create_policy_engine_error(self, policy_client):
        """Test policy engine creation error."""
        mock_client = Mock()
        policy_client.client = mock_client
        mock_client.create_policy_engine.side_effect = Exception("API Error")

        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.create_policy_engine(name="TestEngine")

        assert "Failed to create policy engine" in str(exc_info.value)

    @patch("time.sleep")
    def test_create_or_get_policy_engine_creates_new(self, mock_sleep, policy_client):
        """Test create_or_get_policy_engine creates new engine."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Mock list returns empty
        mock_client.list_policy_engines.return_value = {"policyEngines": []}

        # Mock create response
        mock_client.create_policy_engine.return_value = {
            "policyEngineId": "new-engine",
            "policyEngineArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy-engine/new-engine",
            "status": "CREATING",
        }

        # Mock get for polling
        mock_client.get_policy_engine.return_value = {
            "policyEngineId": "new-engine",
            "status": "ACTIVE",
        }

        result = policy_client.create_or_get_policy_engine(name="NewEngine")

        assert result["policyEngineId"] == "new-engine"
        assert result["status"] == "ACTIVE"
        mock_client.create_policy_engine.assert_called_once()

    @patch("time.sleep")
    def test_create_or_get_policy_engine_finds_existing(self, mock_sleep, policy_client):
        """Test create_or_get_policy_engine finds existing engine."""
        mock_client = Mock()
        policy_client.client = mock_client

        existing_engine = {
            "policyEngineId": "existing-engine",
            "name": "ExistingEngine",
            "status": "ACTIVE",
        }

        mock_client.list_policy_engines.return_value = {"policyEngines": [existing_engine]}

        result = policy_client.create_or_get_policy_engine(name="ExistingEngine")

        assert result["policyEngineId"] == "existing-engine"
        mock_client.create_policy_engine.assert_not_called()

    def test_get_policy_engine_success(self, policy_client):
        """Test get policy engine success."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_response = {"policyEngineId": "engine-123", "status": "ACTIVE"}
        mock_client.get_policy_engine.return_value = mock_response

        result = policy_client.get_policy_engine("engine-123")

        assert result == mock_response
        mock_client.get_policy_engine.assert_called_once_with(policyEngineId="engine-123")

    def test_get_policy_engine_not_found(self, policy_client):
        """Test get policy engine not found."""
        mock_client = Mock()
        policy_client.client = mock_client
        mock_client.exceptions.ResourceNotFoundException = Exception
        mock_client.get_policy_engine.side_effect = mock_client.exceptions.ResourceNotFoundException("Not found")

        with pytest.raises(PolicyEngineNotFoundException):
            policy_client.get_policy_engine("nonexistent")

    def test_update_policy_engine_success(self, policy_client):
        """Test update policy engine."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_response = {
            "policyEngineId": "engine-123",
            "policyEngineArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy-engine/engine-123",
            "description": "Updated",
        }
        mock_client.update_policy_engine.return_value = mock_response

        result = policy_client.update_policy_engine(policy_engine_id="engine-123", description="Updated")

        assert result == mock_response
        mock_client.update_policy_engine.assert_called_once()

    def test_list_policy_engines_basic(self, policy_client):
        """Test list policy engines."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_response = {"policyEngines": [{"policyEngineId": "engine-1"}, {"policyEngineId": "engine-2"}]}
        mock_client.list_policy_engines.return_value = mock_response

        result = policy_client.list_policy_engines()

        assert result == mock_response
        mock_client.list_policy_engines.assert_called_once()

    def test_list_policy_engines_with_pagination(self, policy_client):
        """Test list policy engines with pagination."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_client.list_policy_engines.return_value = {"policyEngines": []}

        policy_client.list_policy_engines(max_results=10, next_token="token123")

        mock_client.list_policy_engines.assert_called_once_with(maxResults=10, nextToken="token123")

    def test_delete_policy_engine_success(self, policy_client):
        """Test delete policy engine."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_response = {"status": "DELETING"}
        mock_client.delete_policy_engine.return_value = mock_response

        result = policy_client.delete_policy_engine("engine-123")

        assert result == mock_response
        mock_client.delete_policy_engine.assert_called_once_with(policyEngineId="engine-123")

    @patch("time.sleep")
    def test_wait_for_policy_engine_active_success(self, mock_sleep, policy_client):
        """Test waiting for policy engine to become active."""
        mock_client = Mock()
        policy_client.client = mock_client

        # First call returns CREATING, second returns ACTIVE
        mock_client.get_policy_engine.side_effect = [
            {"policyEngineId": "engine-123", "status": "CREATING"},
            {"policyEngineId": "engine-123", "status": "ACTIVE"},
        ]

        result = policy_client._wait_for_policy_engine_active("engine-123")

        assert result["status"] == "ACTIVE"
        assert mock_client.get_policy_engine.call_count == 2

    @patch("time.sleep")
    def test_wait_for_policy_engine_timeout(self, mock_sleep, policy_client):
        """Test policy engine wait timeout."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Always return CREATING
        mock_client.get_policy_engine.return_value = {"status": "CREATING"}

        with pytest.raises(TimeoutError):
            policy_client._wait_for_policy_engine_active("engine-123", max_attempts=3)

    @patch("time.sleep")
    def test_wait_for_policy_engine_failed_status(self, mock_sleep, policy_client):
        """Test policy engine enters failed state."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_client.get_policy_engine.return_value = {"status": "FAILED", "statusReasons": ["Error occurred"]}

        with pytest.raises(PolicySetupException) as exc_info:
            policy_client._wait_for_policy_engine_active("engine-123")

        assert "unexpected status" in str(exc_info.value)


class TestPolicyOperations:
    """Test policy CRUD operations."""

    def test_create_policy_success(self, policy_client):
        """Test successful policy creation."""
        mock_client = Mock()
        policy_client.client = mock_client

        definition = {"cedar": {"statement": "permit(principal, action, resource);"}}
        mock_response = {
            "policyId": "policy-123",
            "policyArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy/policy-123",
            "status": "CREATING",
        }
        mock_client.create_policy.return_value = mock_response

        result = policy_client.create_policy(
            policy_engine_id="engine-123", name="TestPolicy", definition=definition, description="Test"
        )

        assert result == mock_response
        mock_client.create_policy.assert_called_once()

    def test_create_policy_with_validation_mode(self, policy_client):
        """Test create policy with validation mode."""
        mock_client = Mock()
        policy_client.client = mock_client

        definition = {"cedar": {"statement": "permit(principal, action, resource);"}}
        mock_client.create_policy.return_value = {
            "policyId": "policy-123",
            "policyArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy/policy-123",
        }

        policy_client.create_policy(
            policy_engine_id="engine-123",
            name="TestPolicy",
            definition=definition,
            validation_mode="FAIL_ON_ANY_FINDINGS",
        )

        call_args = mock_client.create_policy.call_args[1]
        assert call_args["validationMode"] == "FAIL_ON_ANY_FINDINGS"

    def test_create_policy_with_client_token(self, policy_client):
        """Test create policy with client token."""
        mock_client = Mock()
        policy_client.client = mock_client

        definition = {"cedar": {"statement": "permit(principal, action, resource);"}}
        mock_client.create_policy.return_value = {
            "policyId": "policy-123",
            "policyArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy/policy-123",
        }

        policy_client.create_policy(
            policy_engine_id="engine-123", name="TestPolicy", definition=definition, client_token="my-policy-token"
        )

        call_args = mock_client.create_policy.call_args[1]
        assert call_args["clientToken"] == "my-policy-token"

    @patch("time.sleep")
    def test_create_or_get_policy_creates_new(self, mock_sleep, policy_client):
        """Test create_or_get_policy creates new policy."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Mock list returns empty
        mock_client.list_policies.return_value = {"policies": []}

        # Mock create
        definition = {"cedar": {"statement": "permit(principal, action, resource);"}}
        mock_client.create_policy.return_value = {
            "policyId": "new-policy",
            "policyArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy/new-policy",
            "status": "CREATING",
        }

        # Mock get for polling
        mock_client.get_policy.return_value = {"policyId": "new-policy", "status": "ACTIVE"}

        result = policy_client.create_or_get_policy(
            policy_engine_id="engine-123", name="NewPolicy", definition=definition
        )

        assert result["policyId"] == "new-policy"
        assert result["status"] == "ACTIVE"

    @patch("time.sleep")
    def test_create_or_get_policy_finds_existing(self, mock_sleep, policy_client):
        """Test create_or_get_policy finds existing policy."""
        mock_client = Mock()
        policy_client.client = mock_client

        existing_policy = {"policyId": "existing-policy", "name": "ExistingPolicy", "status": "ACTIVE"}

        mock_client.list_policies.return_value = {"policies": [existing_policy]}

        definition = {"cedar": {"statement": "permit(principal, action, resource);"}}
        result = policy_client.create_or_get_policy(
            policy_engine_id="engine-123", name="ExistingPolicy", definition=definition
        )

        assert result["policyId"] == "existing-policy"
        mock_client.create_policy.assert_not_called()

    def test_get_policy_success(self, policy_client):
        """Test get policy success."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_response = {"policyId": "policy-123", "status": "ACTIVE"}
        mock_client.get_policy.return_value = mock_response

        result = policy_client.get_policy("engine-123", "policy-123")

        assert result == mock_response
        mock_client.get_policy.assert_called_once_with(policyEngineId="engine-123", policyId="policy-123")

    def test_get_policy_not_found(self, policy_client):
        """Test get policy not found."""
        mock_client = Mock()
        policy_client.client = mock_client
        mock_client.exceptions.ResourceNotFoundException = Exception
        mock_client.get_policy.side_effect = mock_client.exceptions.ResourceNotFoundException("Not found")

        with pytest.raises(PolicyNotFoundException):
            policy_client.get_policy("engine-123", "nonexistent")

    def test_update_policy_success(self, policy_client):
        """Test update policy."""
        mock_client = Mock()
        policy_client.client = mock_client

        definition = {"cedar": {"statement": "permit(principal, action, resource) when { true };"}}
        mock_response = {
            "policyId": "policy-123",
            "policyArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy/policy-123",
        }
        mock_client.update_policy.return_value = mock_response

        result = policy_client.update_policy(
            policy_engine_id="engine-123", policy_id="policy-123", definition=definition
        )

        assert result == mock_response
        mock_client.update_policy.assert_called_once()

    def test_update_policy_with_validation_mode(self, policy_client):
        """Test update policy with validation mode."""
        mock_client = Mock()
        policy_client.client = mock_client

        definition = {"cedar": {"statement": "permit(principal, action, resource);"}}
        mock_client.update_policy.return_value = {
            "policyId": "policy-123",
            "policyArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy/policy-123",
        }

        policy_client.update_policy(
            policy_engine_id="engine-123",
            policy_id="policy-123",
            definition=definition,
            description="Updated description",
            validation_mode="IGNORE_ALL_FINDINGS",
        )

        call_args = mock_client.update_policy.call_args[1]
        assert call_args["validationMode"] == "IGNORE_ALL_FINDINGS"
        assert call_args["description"] == "Updated description"

    def test_list_policies_basic(self, policy_client):
        """Test list policies."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_response = {"policies": [{"policyId": "p1"}, {"policyId": "p2"}]}
        mock_client.list_policies.return_value = mock_response

        result = policy_client.list_policies("engine-123")

        assert result == mock_response

    def test_list_policies_with_resource_scope(self, policy_client):
        """Test list policies with resource scope filter."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_client.list_policies.return_value = {"policies": []}

        policy_client.list_policies(
            "engine-123", target_resource_scope="arn:aws:bedrock-agentcore:us-east-1:123:gateway/my-gateway"
        )

        call_args = mock_client.list_policies.call_args[1]
        assert "targetResourceScope" in call_args
        assert call_args["targetResourceScope"] == "arn:aws:bedrock-agentcore:us-east-1:123:gateway/my-gateway"

    def test_list_policies_with_pagination(self, policy_client):
        """Test list policies with pagination."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_client.list_policies.return_value = {"policies": []}

        policy_client.list_policies("engine-123", max_results=10, next_token="token123")

        call_args = mock_client.list_policies.call_args[1]
        assert call_args["maxResults"] == 10
        assert call_args["nextToken"] == "token123"

    def test_delete_policy_success(self, policy_client):
        """Test delete policy."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_response = {"status": "DELETING"}
        mock_client.delete_policy.return_value = mock_response

        result = policy_client.delete_policy("engine-123", "policy-123")

        assert result == mock_response
        mock_client.delete_policy.assert_called_once_with(policyEngineId="engine-123", policyId="policy-123")

    @patch("time.sleep")
    def test_wait_for_policy_active_success(self, mock_sleep, policy_client):
        """Test waiting for policy to become active."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_client.get_policy.side_effect = [
            {"policyId": "policy-123", "status": "CREATING"},
            {"policyId": "policy-123", "status": "ACTIVE"},
        ]

        result = policy_client._wait_for_policy_active("engine-123", "policy-123")

        assert result["status"] == "ACTIVE"
        assert mock_client.get_policy.call_count == 2

    @patch("time.sleep")
    def test_wait_for_policy_timeout(self, mock_sleep, policy_client):
        """Test policy wait timeout."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_client.get_policy.return_value = {"status": "CREATING"}

        with pytest.raises(TimeoutError):
            policy_client._wait_for_policy_active("engine-123", "policy-123", max_attempts=3)


class TestPolicyGenerationOperations:
    """Test policy generation operations."""

    def test_start_policy_generation_success(self, policy_client):
        """Test start policy generation."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_response = {
            "policyGenerationId": "gen-123",
            "policyGenerationArn": "arn:aws:bedrock-agentcore:us-east-1:123:generation/gen-123",
            "status": "IN_PROGRESS",
        }
        mock_client.start_policy_generation.return_value = mock_response

        resource = {"arn": "arn:aws:bedrock-agentcore:us-east-1:123:gateway/my-gateway"}
        content = {"rawText": "Allow refunds under $1000"}

        result = policy_client.start_policy_generation(
            policy_engine_id="engine-123", name="test-gen", resource=resource, content=content
        )

        assert result == mock_response
        mock_client.start_policy_generation.assert_called_once()

    def test_start_policy_generation_error(self, policy_client):
        """Test start policy generation error."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Mock the exceptions attribute properly
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        mock_client.start_policy_generation.side_effect = Exception("API Error")

        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.start_policy_generation(
                policy_engine_id="engine-123", name="test", resource={"arn": "arn"}, content={"rawText": "text"}
            )

        assert "Failed to start policy generation" in str(exc_info.value)

    def test_get_policy_generation_success(self, policy_client):
        """Test get policy generation."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_response = {"policyGenerationId": "gen-123", "status": "COMPLETED"}
        mock_client.get_policy_generation.return_value = mock_response

        result = policy_client.get_policy_generation("engine-123", "gen-123")

        assert result == mock_response
        mock_client.get_policy_generation.assert_called_once_with(
            policyEngineId="engine-123", policyGenerationId="gen-123"
        )

    def test_get_policy_generation_not_found(self, policy_client):
        """Test get policy generation not found."""
        mock_client = Mock()
        policy_client.client = mock_client
        mock_client.exceptions.ResourceNotFoundException = Exception
        mock_client.get_policy_generation.side_effect = mock_client.exceptions.ResourceNotFoundException("Not found")

        with pytest.raises(PolicyGenerationNotFoundException):
            policy_client.get_policy_generation("engine-123", "nonexistent")

    def test_list_policy_generation_assets(self, policy_client):
        """Test list policy generation assets."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_response = {"assets": [{"assetId": "asset-1"}]}
        mock_client.list_policy_generation_assets.return_value = mock_response

        result = policy_client.list_policy_generation_assets("engine-123", "gen-123")

        assert result == mock_response

    def test_list_policy_generation_assets_with_pagination(self, policy_client):
        """Test list policy generation assets with pagination."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_client.list_policy_generation_assets.return_value = {"assets": []}

        policy_client.list_policy_generation_assets("engine-123", "gen-123", max_results=5, next_token="token")

        call_args = mock_client.list_policy_generation_assets.call_args[1]
        assert call_args["maxResults"] == 5
        assert call_args["nextToken"] == "token"

    def test_list_policy_generations_basic(self, policy_client):
        """Test list policy generations."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_response = {"generations": [{"policyGenerationId": "gen-1"}]}
        mock_client.list_policy_generations.return_value = mock_response

        result = policy_client.list_policy_generations("engine-123")

        assert result == mock_response


class TestPolicyGenerationWithAssets:
    """Test policy generation with asset fetching."""

    @patch("time.sleep")
    def test_generate_policy_with_fetch_assets_true(self, mock_sleep, policy_client):
        """Test generate_policy with fetch_assets=True."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Mock start generation
        mock_client.start_policy_generation.return_value = {
            "policyGenerationId": "gen-123",
            "policyGenerationArn": "arn:aws:bedrock-agentcore:us-east-1:123:generation/gen-123",
            "status": "GENERATING",
        }

        # Mock get generation (first GENERATING, then GENERATED)
        mock_client.get_policy_generation.side_effect = [
            {"policyGenerationId": "gen-123", "status": "GENERATING"},
            {"policyGenerationId": "gen-123", "status": "GENERATED"},
        ]

        # Mock list assets
        mock_client.list_policy_generation_assets.return_value = {
            "policyGenerationAssets": [
                {"assetId": "asset-1", "definition": {"cedar": {"statement": "permit(...)"}}},
                {"assetId": "asset-2", "definition": {"cedar": {"statement": "forbid(...)"}}},
            ]
        }

        resource = {"arn": "arn:aws:bedrock-agentcore:us-east-1:123:gateway/my-gateway"}
        content = {"rawText": "Allow refunds under $1000"}

        result = policy_client.generate_policy(
            policy_engine_id="engine-123",
            name="test-gen",
            resource=resource,
            content=content,
            fetch_assets=True,
        )

        assert result["status"] == "GENERATED"
        assert "generatedPolicies" in result
        assert len(result["generatedPolicies"]) == 2
        mock_client.list_policy_generation_assets.assert_called_once()

    @patch("time.sleep")
    def test_generate_policy_with_fetch_assets_false(self, mock_sleep, policy_client):
        """Test generate_policy with fetch_assets=False (default)."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_client.start_policy_generation.return_value = {
            "policyGenerationId": "gen-123",
            "policyGenerationArn": "arn:aws:bedrock-agentcore:us-east-1:123:generation/gen-123",
            "status": "GENERATING",
        }

        mock_client.get_policy_generation.return_value = {
            "policyGenerationId": "gen-123",
            "status": "GENERATED",
        }

        resource = {"arn": "arn:aws:bedrock-agentcore:us-east-1:123:gateway/my-gateway"}
        content = {"rawText": "Allow refunds"}

        result = policy_client.generate_policy(
            policy_engine_id="engine-123",
            name="test-gen",
            resource=resource,
            content=content,
            fetch_assets=False,
        )

        assert result["status"] == "GENERATED"
        assert "generatedPolicies" not in result
        mock_client.list_policy_generation_assets.assert_not_called()

    @patch("time.sleep")
    def test_generate_policy_timeout(self, mock_sleep, policy_client):
        """Test generate_policy timeout."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_client.start_policy_generation.return_value = {
            "policyGenerationId": "gen-123",
            "policyGenerationArn": "arn:aws:bedrock-agentcore:us-east-1:123:generation/gen-123",
        }
        mock_client.get_policy_generation.return_value = {"status": "GENERATING"}

        with pytest.raises(TimeoutError):
            policy_client.generate_policy(
                policy_engine_id="engine-123",
                name="test",
                resource={"arn": "arn"},
                content={"rawText": "text"},
                max_attempts=3,
            )

    @patch("time.sleep")
    def test_generate_policy_failed_status(self, mock_sleep, policy_client):
        """Test generate_policy with GENERATE_FAILED status."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_client.start_policy_generation.return_value = {
            "policyGenerationId": "gen-123",
            "policyGenerationArn": "arn:aws:bedrock-agentcore:us-east-1:123:generation/gen-123",
        }
        mock_client.get_policy_generation.return_value = {
            "status": "GENERATE_FAILED",
            "statusReasons": ["Invalid input"],
        }

        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.generate_policy(
                policy_engine_id="engine-123",
                name="test",
                resource={"arn": "arn"},
                content={"rawText": "text"},
            )

        assert "failed with status" in str(exc_info.value)


class TestPaginationInCreateOrGet:
    """Test pagination in create_or_get methods."""

    @patch("time.sleep")
    def test_create_or_get_policy_engine_with_pagination(self, mock_sleep, policy_client):
        """Test create_or_get_policy_engine handles pagination."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Mock paginated list responses
        mock_client.list_policy_engines.side_effect = [
            {"policyEngines": [{"policyEngineId": "e1", "name": "Other"}], "nextToken": "token1"},
            {"policyEngines": [{"policyEngineId": "e2", "name": "Target", "status": "ACTIVE"}]},
        ]

        result = policy_client.create_or_get_policy_engine(name="Target")

        assert result["policyEngineId"] == "e2"
        assert mock_client.list_policy_engines.call_count == 2
        mock_client.create_policy_engine.assert_not_called()

    @patch("time.sleep")
    def test_create_or_get_policy_engine_conflict_exception(self, mock_sleep, policy_client):
        """Test create_or_get_policy_engine handles ConflictException."""
        mock_client = Mock()
        policy_client.client = mock_client

        # First list returns empty
        mock_client.list_policy_engines.side_effect = [
            {"policyEngines": []},
            # After ConflictException, list again and find it
            {"policyEngines": [{"policyEngineId": "e1", "name": "TestEngine", "status": "CREATING"}]},
        ]

        # Create raises ConflictException
        mock_client.create_policy_engine.side_effect = PolicySetupException("ConflictException: already exists")

        # Get for polling
        mock_client.get_policy_engine.return_value = {"policyEngineId": "e1", "status": "ACTIVE"}

        result = policy_client.create_or_get_policy_engine(name="TestEngine")

        assert result["policyEngineId"] == "e1"
        assert result["status"] == "ACTIVE"

    @patch("time.sleep")
    def test_create_or_get_policy_with_pagination(self, mock_sleep, policy_client):
        """Test create_or_get_policy handles pagination."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Mock paginated list responses
        mock_client.list_policies.side_effect = [
            {"policies": [{"policyId": "p1", "name": "Other"}], "nextToken": "token1"},
            {"policies": [{"policyId": "p2", "name": "Target", "status": "ACTIVE"}]},
        ]

        definition = {"cedar": {"statement": "permit(...)"}}
        result = policy_client.create_or_get_policy(policy_engine_id="engine-123", name="Target", definition=definition)

        assert result["policyId"] == "p2"
        assert mock_client.list_policies.call_count == 2
        mock_client.create_policy.assert_not_called()

    @patch("time.sleep")
    def test_create_or_get_policy_conflict_exception(self, mock_sleep, policy_client):
        """Test create_or_get_policy handles ConflictException."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        # First list returns empty
        mock_client.list_policies.side_effect = [
            {"policies": []},
            # After ConflictException, list again and find it
            {"policies": [{"policyId": "p1", "name": "TestPolicy", "status": "CREATING"}]},
        ]

        # Create raises ConflictException
        definition = {"cedar": {"statement": "permit(...)"}}
        mock_client.create_policy.side_effect = PolicySetupException("ConflictException: already exists")

        # Get for polling
        mock_client.get_policy.return_value = {"policyId": "p1", "status": "ACTIVE"}

        result = policy_client.create_or_get_policy(
            policy_engine_id="engine-123", name="TestPolicy", definition=definition
        )

        assert result["policyId"] == "p1"
        assert result["status"] == "ACTIVE"


class TestWaitForPolicyDeleted:
    """Test _wait_for_policy_deleted helper."""

    @patch("time.sleep")
    def test_wait_for_policy_deleted_success(self, mock_sleep, policy_client):
        """Test waiting for policy deletion to complete."""
        mock_client = Mock()
        policy_client.client = mock_client

        # First call returns DELETING, second raises ResourceNotFoundException
        mock_client.exceptions.ResourceNotFoundException = PolicyNotFoundException
        mock_client.get_policy.side_effect = [
            {"policyId": "p1", "status": "DELETING"},
            PolicyNotFoundException("Not found"),
        ]

        # Should not raise
        policy_client._wait_for_policy_deleted("engine-123", "p1")

        assert mock_client.get_policy.call_count == 2

    @patch("time.sleep")
    def test_wait_for_policy_deleted_timeout(self, mock_sleep, policy_client):
        """Test timeout waiting for policy deletion."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Always returns DELETING
        mock_client.get_policy.return_value = {"status": "DELETING"}

        with pytest.raises(TimeoutError) as exc_info:
            policy_client._wait_for_policy_deleted("engine-123", "p1", max_attempts=3)

        assert "not deleted after" in str(exc_info.value)

    @patch("time.sleep")
    def test_wait_for_policy_deleted_unexpected_status(self, mock_sleep, policy_client):
        """Test policy enters unexpected status during deletion."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_client.get_policy.return_value = {"status": "ACTIVE"}

        with pytest.raises(PolicySetupException) as exc_info:
            policy_client._wait_for_policy_deleted("engine-123", "p1")

        assert "unexpected status during deletion" in str(exc_info.value)


class TestExceptionHandling:
    """Test exception handling in various operations."""

    def test_create_policy_generic_exception(self, policy_client):
        """Test create_policy with generic exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        # Mock generic exception (not ResourceNotFoundException)
        mock_client.create_policy.side_effect = Exception("Unexpected error")

        definition = {"cedar": {"statement": "permit(...)"}}
        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.create_policy(policy_engine_id="engine-123", name="TestPolicy", definition=definition)

        assert "Failed to create policy" in str(exc_info.value)

    def test_update_policy_generic_exception(self, policy_client):
        """Test update_policy with generic exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        mock_client.update_policy.side_effect = Exception("Unexpected error")

        definition = {"cedar": {"statement": "permit(...)"}}
        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.update_policy(policy_engine_id="engine-123", policy_id="policy-123", definition=definition)

        assert "Failed to update policy" in str(exc_info.value)

    def test_delete_policy_generic_exception(self, policy_client):
        """Test delete_policy with generic exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        mock_client.delete_policy.side_effect = Exception("Unexpected error")

        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.delete_policy("engine-123", "policy-123")

        assert "Failed to delete policy" in str(exc_info.value)

    def test_update_policy_not_found(self, policy_client):
        """Test update_policy with policy not found."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        ResourceNotFoundError = type("ResourceNotFoundException", (Exception,), {})
        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundError
        mock_client.update_policy.side_effect = ResourceNotFoundError("Not found")

        definition = {"cedar": {"statement": "permit(...)"}}
        with pytest.raises(PolicyNotFoundException):
            policy_client.update_policy(policy_engine_id="engine-123", policy_id="nonexistent", definition=definition)

    def test_delete_policy_not_found(self, policy_client):
        """Test delete_policy with policy not found."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        ResourceNotFoundError = type("ResourceNotFoundException", (Exception,), {})
        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundError
        mock_client.delete_policy.side_effect = ResourceNotFoundError("Not found")

        with pytest.raises(PolicyNotFoundException):
            policy_client.delete_policy("engine-123", "nonexistent")

    def test_start_policy_generation_engine_not_found(self, policy_client):
        """Test start_policy_generation with engine not found."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        ResourceNotFoundError = type("ResourceNotFoundException", (Exception,), {})
        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundError
        mock_client.start_policy_generation.side_effect = ResourceNotFoundError("Engine not found")

        with pytest.raises(PolicyEngineNotFoundException):
            policy_client.start_policy_generation(
                policy_engine_id="nonexistent", name="test", resource={"arn": "arn"}, content={"rawText": "text"}
            )

    def test_list_policy_generation_assets_not_found(self, policy_client):
        """Test list_policy_generation_assets with generation not found."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        ResourceNotFoundError = type("ResourceNotFoundException", (Exception,), {})
        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundError
        mock_client.list_policy_generation_assets.side_effect = ResourceNotFoundError("Not found")

        with pytest.raises(PolicyGenerationNotFoundException):
            policy_client.list_policy_generation_assets("engine-123", "nonexistent")

    def test_list_policy_generation_assets_generic_exception(self, policy_client):
        """Test list_policy_generation_assets with generic exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        mock_client.list_policy_generation_assets.side_effect = Exception("Unexpected error")

        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.list_policy_generation_assets("engine-123", "gen-123")

        assert "Failed to get policy generation assets" in str(exc_info.value)

    def test_list_policy_generations_engine_not_found(self, policy_client):
        """Test list_policy_generations with engine not found."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        ResourceNotFoundError = type("ResourceNotFoundException", (Exception,), {})
        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundError
        mock_client.list_policy_generations.side_effect = ResourceNotFoundError("Engine not found")

        with pytest.raises(PolicyEngineNotFoundException):
            policy_client.list_policy_generations("nonexistent")

    def test_list_policy_generations_generic_exception(self, policy_client):
        """Test list_policy_generations with generic exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        mock_client.list_policy_generations.side_effect = Exception("Unexpected error")

        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.list_policy_generations("engine-123")

        assert "Failed to list policy generations" in str(exc_info.value)

    def test_get_policy_generation_generic_exception(self, policy_client):
        """Test get_policy_generation with generic exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        mock_client.get_policy_generation.side_effect = Exception("Unexpected error")

        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.get_policy_generation("engine-123", "gen-123")

        assert "Failed to get policy generation" in str(exc_info.value)

    @patch("time.sleep")
    def test_wait_for_policy_engine_generic_exception(self, mock_sleep, policy_client):
        """Test _wait_for_policy_engine_active with unexpected exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        mock_client.get_policy_engine.side_effect = Exception("Unexpected error")

        with pytest.raises(Exception) as exc_info:
            policy_client._wait_for_policy_engine_active("engine-123")

        assert "Unexpected error" in str(exc_info.value)

    @patch("time.sleep")
    def test_wait_for_policy_generic_exception(self, mock_sleep, policy_client):
        """Test _wait_for_policy_active with unexpected exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        mock_client.get_policy.side_effect = Exception("Unexpected error")

        with pytest.raises(Exception) as exc_info:
            policy_client._wait_for_policy_active("engine-123", "policy-123")

        assert "Unexpected error" in str(exc_info.value)

    @patch("time.sleep")
    def test_wait_for_policy_deleted_generic_exception(self, mock_sleep, policy_client):
        """Test _wait_for_policy_deleted with unexpected exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        # Not a ResourceNotFoundException
        mock_client.get_policy.side_effect = Exception("Unexpected error")

        with pytest.raises(Exception) as exc_info:
            policy_client._wait_for_policy_deleted("engine-123", "policy-123")

        assert "Unexpected error" in str(exc_info.value)


class TestAdditionalEdgeCases:
    """Test additional edge cases and error paths."""

    def test_update_policy_engine_with_no_description(self, policy_client):
        """Test update_policy_engine without description."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_response = {
            "policyEngineId": "engine-123",
            "policyEngineArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy-engine/engine-123",
        }
        mock_client.update_policy_engine.return_value = mock_response

        result = policy_client.update_policy_engine(policy_engine_id="engine-123")

        assert result == mock_response
        # Should only have policyEngineId in request
        call_args = mock_client.update_policy_engine.call_args[1]
        assert "description" not in call_args

    def test_update_policy_engine_not_found(self, policy_client):
        """Test update_policy_engine with engine not found."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        ResourceNotFoundError = type("ResourceNotFoundException", (Exception,), {})
        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundError
        mock_client.update_policy_engine.side_effect = ResourceNotFoundError("Not found")

        with pytest.raises(PolicyEngineNotFoundException):
            policy_client.update_policy_engine(policy_engine_id="nonexistent", description="test")

    def test_list_policy_engines_generic_exception(self, policy_client):
        """Test list_policy_engines with generic exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_client.list_policy_engines.side_effect = Exception("Unexpected error")

        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.list_policy_engines()

        assert "Failed to list policy engines" in str(exc_info.value)

    def test_delete_policy_engine_not_found(self, policy_client):
        """Test delete_policy_engine with engine not found."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        ResourceNotFoundError = type("ResourceNotFoundException", (Exception,), {})
        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundError
        mock_client.delete_policy_engine.side_effect = ResourceNotFoundError("Not found")

        with pytest.raises(PolicyEngineNotFoundException):
            policy_client.delete_policy_engine("nonexistent")

    def test_create_policy_without_optional_params(self, policy_client):
        """Test create_policy without optional parameters."""
        mock_client = Mock()
        policy_client.client = mock_client

        definition = {"cedar": {"statement": "permit(principal, action, resource);"}}
        mock_response = {
            "policyId": "policy-123",
            "policyArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy/policy-123",
        }
        mock_client.create_policy.return_value = mock_response

        result = policy_client.create_policy(policy_engine_id="engine-123", name="TestPolicy", definition=definition)

        assert result == mock_response
        call_args = mock_client.create_policy.call_args[1]
        assert "description" not in call_args
        assert "validationMode" not in call_args
        assert "clientToken" not in call_args

    def test_update_policy_without_optional_params(self, policy_client):
        """Test update_policy without optional parameters."""
        mock_client = Mock()
        policy_client.client = mock_client

        definition = {"cedar": {"statement": "permit(principal, action, resource);"}}
        mock_response = {
            "policyId": "policy-123",
            "policyArn": "arn:aws:bedrock-agentcore:us-east-1:123:policy/policy-123",
        }
        mock_client.update_policy.return_value = mock_response

        result = policy_client.update_policy(
            policy_engine_id="engine-123", policy_id="policy-123", definition=definition
        )

        assert result == mock_response
        call_args = mock_client.update_policy.call_args[1]
        assert "description" not in call_args
        assert "validationMode" not in call_args

    def test_list_policies_engine_not_found(self, policy_client):
        """Test list_policies with engine not found."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        ResourceNotFoundError = type("ResourceNotFoundException", (Exception,), {})
        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundError
        mock_client.list_policies.side_effect = ResourceNotFoundError("Not found")

        with pytest.raises(PolicyEngineNotFoundException):
            policy_client.list_policies("nonexistent")

    def test_list_policies_generic_exception(self, policy_client):
        """Test list_policies with generic exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        mock_client.list_policies.side_effect = Exception("Unexpected error")

        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.list_policies("engine-123")

        assert "Failed to list policies" in str(exc_info.value)

    def test_start_policy_generation_without_client_token(self, policy_client):
        """Test start_policy_generation without client token."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_response = {
            "policyGenerationId": "gen-123",
            "policyGenerationArn": "arn:aws:bedrock-agentcore:us-east-1:123:generation/gen-123",
        }
        mock_client.start_policy_generation.return_value = mock_response

        resource = {"arn": "arn:aws:bedrock-agentcore:us-east-1:123:gateway/my-gateway"}
        content = {"rawText": "Allow refunds"}

        result = policy_client.start_policy_generation(
            policy_engine_id="engine-123", name="test-gen", resource=resource, content=content
        )

        assert result == mock_response
        call_args = mock_client.start_policy_generation.call_args[1]
        assert "clientToken" not in call_args

    def test_get_policy_generic_exception(self, policy_client):
        """Test get_policy with generic exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        mock_client.get_policy.side_effect = Exception("Unexpected error")

        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.get_policy("engine-123", "policy-123")

        assert "Failed to get policy" in str(exc_info.value)

    def test_update_policy_engine_generic_exception(self, policy_client):
        """Test update_policy_engine with generic exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        mock_client.update_policy_engine.side_effect = Exception("Unexpected error")

        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.update_policy_engine(policy_engine_id="engine-123", description="test")

        assert "Failed to update policy engine" in str(exc_info.value)

    def test_get_policy_engine_generic_exception(self, policy_client):
        """Test get_policy_engine with generic exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        mock_client.get_policy_engine.side_effect = Exception("Unexpected error")

        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.get_policy_engine("engine-123")

        assert "Failed to get policy engine" in str(exc_info.value)

    def test_delete_policy_engine_generic_exception(self, policy_client):
        """Test delete_policy_engine with generic exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        mock_client.delete_policy_engine.side_effect = Exception("Unexpected error")

        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.delete_policy_engine("engine-123")

        assert "Failed to delete policy engine" in str(exc_info.value)

    def test_create_policy_engine_not_found(self, policy_client):
        """Test create_policy_engine with engine not found exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        ResourceNotFoundError = type("ResourceNotFoundException", (Exception,), {})
        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundError
        mock_client.create_policy_engine.side_effect = ResourceNotFoundError("Not found")

        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.create_policy_engine(name="TestEngine")

        assert "Failed to create policy engine" in str(exc_info.value)

    def test_create_policy_not_found(self, policy_client):
        """Test create_policy with policy not found exception."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions properly
        mock_client.exceptions = Mock()
        ResourceNotFoundError = type("ResourceNotFoundException", (Exception,), {})
        mock_client.exceptions.ResourceNotFoundException = ResourceNotFoundError
        mock_client.create_policy.side_effect = ResourceNotFoundError("Engine not found")

        definition = {"cedar": {"statement": "permit(...)"}}
        with pytest.raises(PolicyEngineNotFoundException):
            policy_client.create_policy(policy_engine_id="nonexistent", name="TestPolicy", definition=definition)


class TestCreateOrGetWithWaitingStatus:
    """Test create_or_get methods finding resources in non-ACTIVE state."""

    @patch("time.sleep")
    def test_create_or_get_policy_engine_finds_creating_engine(self, mock_sleep, policy_client):
        """Test create_or_get_policy_engine finds existing CREATING engine."""
        mock_client = Mock()
        policy_client.client = mock_client

        # First list finds CREATING engine
        existing_engine = {
            "policyEngineId": "e1",
            "name": "TestEngine",
            "status": "CREATING",
        }
        mock_client.list_policy_engines.return_value = {"policyEngines": [existing_engine]}

        # Mock get for waiting
        mock_client.get_policy_engine.return_value = {
            "policyEngineId": "e1",
            "status": "ACTIVE",
        }

        result = policy_client.create_or_get_policy_engine(name="TestEngine")

        assert result["policyEngineId"] == "e1"
        assert result["status"] == "ACTIVE"
        mock_client.create_policy_engine.assert_not_called()
        mock_client.get_policy_engine.assert_called_once()

    @patch("time.sleep")
    def test_create_or_get_policy_engine_conflict_not_found_after_retry(self, mock_sleep, policy_client):
        """Test create_or_get_policy_engine ConflictException but engine not found after retry."""
        mock_client = Mock()
        policy_client.client = mock_client

        # First list returns empty
        mock_client.list_policy_engines.side_effect = [
            {"policyEngines": []},
            # After ConflictException, list again but still not found
            {"policyEngines": []},
        ]

        # Create raises ConflictException
        mock_client.create_policy_engine.side_effect = PolicySetupException("ConflictException: already exists")

        # Should raise the original ConflictException
        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.create_or_get_policy_engine(name="TestEngine")

        assert "ConflictException" in str(exc_info.value)

    @patch("time.sleep")
    def test_create_or_get_policy_finds_creating_policy(self, mock_sleep, policy_client):
        """Test create_or_get_policy finds existing CREATING policy."""
        mock_client = Mock()
        policy_client.client = mock_client

        # First list finds CREATING policy
        existing_policy = {
            "policyId": "p1",
            "name": "TestPolicy",
            "status": "CREATING",
        }
        mock_client.list_policies.return_value = {"policies": [existing_policy]}

        # Mock get for waiting
        mock_client.get_policy.return_value = {
            "policyId": "p1",
            "status": "ACTIVE",
        }

        definition = {"cedar": {"statement": "permit(...)"}}
        result = policy_client.create_or_get_policy(
            policy_engine_id="engine-123", name="TestPolicy", definition=definition
        )

        assert result["policyId"] == "p1"
        assert result["status"] == "ACTIVE"
        mock_client.create_policy.assert_not_called()
        mock_client.get_policy.assert_called_once()

    @patch("time.sleep")
    def test_create_or_get_policy_conflict_not_found_after_retry(self, mock_sleep, policy_client):
        """Test create_or_get_policy ConflictException but policy not found after retry."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Setup exceptions
        mock_client.exceptions = Mock()
        mock_client.exceptions.ResourceNotFoundException = type("ResourceNotFoundException", (Exception,), {})

        # First list returns empty
        mock_client.list_policies.side_effect = [
            {"policies": []},
            # After ConflictException, list again but still not found
            {"policies": []},
        ]

        # Create raises ConflictException
        definition = {"cedar": {"statement": "permit(...)"}}
        mock_client.create_policy.side_effect = PolicySetupException("ConflictException: already exists")

        # Should raise the original ConflictException
        with pytest.raises(PolicySetupException) as exc_info:
            policy_client.create_or_get_policy(policy_engine_id="engine-123", name="TestPolicy", definition=definition)

        assert "ConflictException" in str(exc_info.value)


class TestDeepPaginationEdgeCases:
    """Test deep pagination scenarios in create_or_get methods."""

    @patch("time.sleep")
    def test_create_or_get_policy_engine_deep_pagination_before_find(self, mock_sleep, policy_client):
        """Test create_or_get_policy_engine with deep pagination before finding engine."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Simulate 3 pages before finding the target
        mock_client.list_policy_engines.side_effect = [
            {"policyEngines": [{"policyEngineId": "e1", "name": "Other1"}], "nextToken": "t1"},
            {"policyEngines": [{"policyEngineId": "e2", "name": "Other2"}], "nextToken": "t2"},
            {"policyEngines": [{"policyEngineId": "e3", "name": "Target", "status": "ACTIVE"}]},
        ]

        result = policy_client.create_or_get_policy_engine(name="Target")

        assert result["policyEngineId"] == "e3"
        assert mock_client.list_policy_engines.call_count == 3

    @patch("time.sleep")
    def test_create_or_get_policy_deep_pagination_before_find(self, mock_sleep, policy_client):
        """Test create_or_get_policy with deep pagination before finding policy."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Simulate 3 pages before finding the target
        mock_client.list_policies.side_effect = [
            {"policies": [{"policyId": "p1", "name": "Other1"}], "nextToken": "t1"},
            {"policies": [{"policyId": "p2", "name": "Other2"}], "nextToken": "t2"},
            {"policies": [{"policyId": "p3", "name": "Target", "status": "ACTIVE"}]},
        ]

        definition = {"cedar": {"statement": "permit(...)"}}
        result = policy_client.create_or_get_policy(policy_engine_id="engine-123", name="Target", definition=definition)

        assert result["policyId"] == "p3"
        assert mock_client.list_policies.call_count == 3


class TestCleanupOperations:
    """Test cleanup operations."""

    @patch("time.sleep")
    def test_cleanup_policy_engine_full_flow(self, mock_sleep, policy_client):
        """Test cleanup policy engine with policies."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Mock list policies
        mock_client.list_policies.side_effect = [
            {"policies": [{"policyId": "p1", "name": "Policy1"}, {"policyId": "p2", "name": "Policy2"}]},
        ]

        # Mock get_policy to simulate deletion
        mock_client.exceptions.ResourceNotFoundException = PolicyNotFoundException
        mock_client.get_policy.side_effect = PolicyNotFoundException("Not found")

        policy_client.cleanup_policy_engine("engine-123")

        # Verify policies deleted
        assert mock_client.delete_policy.call_count == 2
        mock_client.delete_policy.assert_any_call(policyEngineId="engine-123", policyId="p1")
        mock_client.delete_policy.assert_any_call(policyEngineId="engine-123", policyId="p2")

        # Verify engine deleted
        mock_client.delete_policy_engine.assert_called_once_with(policyEngineId="engine-123")

    @patch("time.sleep")
    def test_cleanup_policy_engine_with_pagination(self, mock_sleep, policy_client):
        """Test cleanup handles paginated policy list."""
        mock_client = Mock()
        policy_client.client = mock_client

        # Mock paginated list
        mock_client.list_policies.side_effect = [
            {"policies": [{"policyId": "p1", "name": "Policy1"}], "nextToken": "token1"},
            {"policies": [{"policyId": "p2", "name": "Policy2"}]},
        ]

        # Mock get_policy
        mock_client.exceptions.ResourceNotFoundException = PolicyNotFoundException
        mock_client.get_policy.side_effect = PolicyNotFoundException("Not found")

        policy_client.cleanup_policy_engine("engine-123")

        # Should have called list_policies twice for pagination
        assert mock_client.list_policies.call_count == 2
        # Should have deleted both policies
        assert mock_client.delete_policy.call_count == 2

    @patch("time.sleep")
    def test_cleanup_policy_engine_with_errors(self, mock_sleep, policy_client):
        """Test cleanup with errors continues gracefully."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_client.list_policies.return_value = {"policies": [{"policyId": "p1", "name": "Policy1"}]}
        mock_client.delete_policy.side_effect = Exception("Delete failed")

        # Should not raise exception
        policy_client.cleanup_policy_engine("engine-123")

    @patch("time.sleep")
    def test_cleanup_policy_engine_list_error(self, mock_sleep, policy_client):
        """Test cleanup when listing fails."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_client.list_policies.side_effect = Exception("List error")

        # Should not raise exception, just log warning
        policy_client.cleanup_policy_engine("engine-123")

        # Should still try to delete engine
        mock_client.delete_policy_engine.assert_called_once()

    @patch("time.sleep")
    def test_cleanup_policy_engine_delete_engine_error(self, mock_sleep, policy_client):
        """Test cleanup when engine deletion fails."""
        mock_client = Mock()
        policy_client.client = mock_client

        mock_client.list_policies.return_value = {"policies": []}
        mock_client.delete_policy_engine.side_effect = Exception("Delete engine failed")

        # Should not raise exception
        policy_client.cleanup_policy_engine("engine-123")
