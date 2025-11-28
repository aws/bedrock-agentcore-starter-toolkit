"""Comprehensive unit tests for evaluator operations.

Tests all evaluator management business logic with data-driven approach.
"""

from unittest.mock import MagicMock

import pytest

from bedrock_agentcore_starter_toolkit.operations.evaluation.evaluator_processor import (
    create_evaluator,
    delete_evaluator,
    duplicate_evaluator,
    filter_custom_evaluators,
    get_evaluator,
    get_evaluator_for_duplication,
    is_builtin_evaluator,
    list_evaluators,
    update_evaluator,
    update_evaluator_instructions,
    validate_evaluator_config,
)

# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def mock_client():
    """Mock control plane client."""
    return MagicMock()


@pytest.fixture
def valid_config():
    """Valid evaluator configuration."""
    return {
        "llmAsAJudge": {
            "instructions": "Evaluate the response for helpfulness",
            "modelId": "anthropic.claude-3-sonnet-20240229-v1:0",
        }
    }


@pytest.fixture
def evaluator_details():
    """Sample evaluator details from API."""
    return {
        "evaluatorId": "Custom.MyEval",
        "evaluatorName": "My Evaluator",
        "evaluatorArn": "arn:aws:bedrock:::evaluator/Custom.MyEval",
        "level": "TRACE",
        "description": "A custom evaluator",
        "evaluatorConfig": {
            "llmAsAJudge": {"instructions": "Evaluate carefully", "modelId": "anthropic.claude-3-sonnet-20240229-v1:0"}
        },
    }


# =============================================================================
# Filtering and Validation Tests
# =============================================================================


class TestFilteringAndValidation:
    """Test filtering and validation functions."""

    @pytest.mark.parametrize(
        "evaluators,expected_count",
        [
            ([], 0),  # Empty list
            ([{"evaluatorId": "Builtin.Helpfulness"}], 0),  # Only builtin
            ([{"evaluatorId": "Custom.MyEval"}], 1),  # Only custom
            (
                [
                    {"evaluatorId": "Builtin.Helpfulness"},
                    {"evaluatorId": "Custom.MyEval"},
                    {"evaluatorId": "Builtin.Accuracy"},
                ],
                1,
            ),  # Mixed
            (
                [{"evaluatorId": "Custom.Eval1"}, {"evaluatorId": "Custom.Eval2"}, {"evaluatorId": "Custom.Eval3"}],
                3,
            ),  # All custom
        ],
    )
    def test_filter_custom_evaluators(self, evaluators, expected_count):
        """Test filtering custom evaluators from list."""
        result = filter_custom_evaluators(evaluators)

        assert len(result) == expected_count
        assert all(not e["evaluatorId"].startswith("Builtin.") for e in result)

    @pytest.mark.parametrize(
        "evaluator_id,expected",
        [
            ("Builtin.Helpfulness", True),
            ("Builtin.Accuracy", True),
            ("Builtin.", True),  # Edge case
            ("Custom.MyEval", False),
            ("MyEvaluator", False),
            ("builtin.Helpfulness", False),  # Case sensitive
            ("", False),  # Empty string
        ],
    )
    def test_is_builtin_evaluator(self, evaluator_id, expected):
        """Test builtin evaluator detection."""
        result = is_builtin_evaluator(evaluator_id)

        assert result == expected

    def test_validate_evaluator_config_valid(self, valid_config):
        """Test validation passes for valid config."""
        # Should not raise
        validate_evaluator_config(valid_config)

    @pytest.mark.parametrize(
        "invalid_config",
        [
            {},  # Empty config
            {"wrongKey": {}},  # Wrong key
            {"llm": {}},  # Typo in key
            {"LlmAsAJudge": {}},  # Wrong case
        ],
    )
    def test_validate_evaluator_config_invalid(self, invalid_config):
        """Test validation fails for invalid configs."""
        with pytest.raises(ValueError, match="llmAsAJudge"):
            validate_evaluator_config(invalid_config)


# =============================================================================
# Evaluator Retrieval Tests
# =============================================================================


class TestEvaluatorRetrieval:
    """Test evaluator retrieval and preparation."""

    def test_get_evaluator_for_duplication_success(self, mock_client, evaluator_details):
        """Test successful retrieval for duplication."""
        mock_client.get_evaluator.return_value = evaluator_details

        config, level, description = get_evaluator_for_duplication(mock_client, "Custom.MyEval")

        assert "llmAsAJudge" in config
        assert level == "TRACE"
        assert description == "A custom evaluator"
        mock_client.get_evaluator.assert_called_once_with(evaluator_id="Custom.MyEval")

    def test_get_evaluator_for_duplication_builtin_fails(self, mock_client):
        """Test duplication fails for builtin evaluators."""
        with pytest.raises(ValueError, match="Built-in evaluators cannot be duplicated"):
            get_evaluator_for_duplication(mock_client, "Builtin.Helpfulness")

        # Client should not be called
        mock_client.get_evaluator.assert_not_called()

    def test_get_evaluator_for_duplication_invalid_config(self, mock_client):
        """Test duplication fails if config is invalid."""
        invalid_details = {
            "evaluatorId": "Custom.MyEval",
            "level": "TRACE",
            "description": "Test",
            "evaluatorConfig": {},  # Missing llmAsAJudge
        }
        mock_client.get_evaluator.return_value = invalid_details

        with pytest.raises(ValueError, match="llmAsAJudge"):
            get_evaluator_for_duplication(mock_client, "Custom.MyEval")

    @pytest.mark.parametrize(
        "missing_field,default_value",
        [
            ("level", "TRACE"),  # Default level
            ("description", ""),  # Default description
        ],
    )
    def test_get_evaluator_for_duplication_missing_fields(
        self, mock_client, evaluator_details, missing_field, default_value
    ):
        """Test handling of missing optional fields."""
        # Remove field
        del evaluator_details[missing_field]
        mock_client.get_evaluator.return_value = evaluator_details

        config, level, description = get_evaluator_for_duplication(mock_client, "Custom.MyEval")

        # Check default is used
        if missing_field == "level":
            assert level == default_value
        elif missing_field == "description":
            assert description == default_value


# =============================================================================
# Evaluator Creation Tests
# =============================================================================


class TestEvaluatorCreation:
    """Test evaluator creation operations."""

    def test_create_evaluator_basic(self, mock_client, valid_config):
        """Test basic evaluator creation."""
        mock_client.create_evaluator.return_value = {
            "evaluatorId": "Custom.NewEval",
            "evaluatorArn": "arn:aws:bedrock:::evaluator/Custom.NewEval",
        }

        result = create_evaluator(mock_client, name="NewEval", config=valid_config)

        assert result["evaluatorId"] == "Custom.NewEval"
        mock_client.create_evaluator.assert_called_once_with(
            name="NewEval", config=valid_config, level="TRACE", description=None
        )

    @pytest.mark.parametrize("level", ["SESSION", "TRACE", "TOOL_CALL"])
    def test_create_evaluator_with_levels(self, mock_client, valid_config, level):
        """Test creating evaluators with different levels."""
        mock_client.create_evaluator.return_value = {"evaluatorId": "Test"}

        create_evaluator(mock_client, name="TestEval", config=valid_config, level=level)

        call_args = mock_client.create_evaluator.call_args
        assert call_args.kwargs["level"] == level

    def test_create_evaluator_with_description(self, mock_client, valid_config):
        """Test creating evaluator with description."""
        mock_client.create_evaluator.return_value = {"evaluatorId": "Test"}

        create_evaluator(mock_client, name="TestEval", config=valid_config, description="This is a test evaluator")

        call_args = mock_client.create_evaluator.call_args
        assert call_args.kwargs["description"] == "This is a test evaluator"

    def test_create_evaluator_invalid_config(self, mock_client):
        """Test creation fails with invalid config."""
        invalid_config = {"wrongKey": {}}

        with pytest.raises(ValueError, match="llmAsAJudge"):
            create_evaluator(mock_client, "Test", invalid_config)

        # Client should not be called
        mock_client.create_evaluator.assert_not_called()

    def test_duplicate_evaluator_success(self, mock_client, evaluator_details):
        """Test successful evaluator duplication."""
        mock_client.get_evaluator.return_value = evaluator_details
        mock_client.create_evaluator.return_value = {
            "evaluatorId": "Custom.Duplicate",
            "evaluatorArn": "arn:aws:bedrock:::evaluator/Custom.Duplicate",
        }

        result = duplicate_evaluator(mock_client, source_evaluator_id="Custom.MyEval", new_name="Duplicate")

        assert result["evaluatorId"] == "Custom.Duplicate"
        # Verify get and create were called
        mock_client.get_evaluator.assert_called_once()
        mock_client.create_evaluator.assert_called_once()

    def test_duplicate_evaluator_with_new_description(self, mock_client, evaluator_details):
        """Test duplication with new description."""
        mock_client.get_evaluator.return_value = evaluator_details
        mock_client.create_evaluator.return_value = {"evaluatorId": "Custom.Dup"}

        duplicate_evaluator(
            mock_client, source_evaluator_id="Custom.MyEval", new_name="Duplicate", new_description="New description"
        )

        call_args = mock_client.create_evaluator.call_args
        assert call_args.kwargs["description"] == "New description"

    def test_duplicate_evaluator_uses_source_description(self, mock_client, evaluator_details):
        """Test duplication uses source description when not provided."""
        mock_client.get_evaluator.return_value = evaluator_details
        mock_client.create_evaluator.return_value = {"evaluatorId": "Custom.Dup"}

        duplicate_evaluator(mock_client, source_evaluator_id="Custom.MyEval", new_name="Duplicate")

        call_args = mock_client.create_evaluator.call_args
        assert call_args.kwargs["description"] == "A custom evaluator"

    def test_duplicate_evaluator_builtin_fails(self, mock_client):
        """Test duplicating builtin evaluator fails."""
        with pytest.raises(ValueError, match="Built-in evaluators cannot be duplicated"):
            duplicate_evaluator(mock_client, source_evaluator_id="Builtin.Helpfulness", new_name="Copy")


# =============================================================================
# Evaluator Update Tests
# =============================================================================


class TestEvaluatorUpdate:
    """Test evaluator update operations."""

    def test_update_evaluator_description_only(self, mock_client):
        """Test updating only description."""
        mock_client.update_evaluator.return_value = {"status": "success"}

        result = update_evaluator(mock_client, evaluator_id="Custom.MyEval", description="Updated description")

        assert result["status"] == "success"
        mock_client.update_evaluator.assert_called_once_with(
            evaluator_id="Custom.MyEval", description="Updated description", config=None
        )

    def test_update_evaluator_config_only(self, mock_client, valid_config):
        """Test updating only config."""
        mock_client.update_evaluator.return_value = {"status": "success"}

        update_evaluator(mock_client, evaluator_id="Custom.MyEval", config=valid_config)

        call_args = mock_client.update_evaluator.call_args
        assert call_args.kwargs["config"] == valid_config
        assert call_args.kwargs["description"] is None

    def test_update_evaluator_both_fields(self, mock_client, valid_config):
        """Test updating both description and config."""
        mock_client.update_evaluator.return_value = {"status": "success"}

        update_evaluator(mock_client, evaluator_id="Custom.MyEval", description="New desc", config=valid_config)

        call_args = mock_client.update_evaluator.call_args
        assert call_args.kwargs["description"] == "New desc"
        assert call_args.kwargs["config"] == valid_config

    def test_update_evaluator_builtin_fails(self, mock_client, valid_config):
        """Test updating builtin evaluator fails."""
        with pytest.raises(ValueError, match="Built-in evaluators cannot be updated"):
            update_evaluator(mock_client, evaluator_id="Builtin.Helpfulness", description="Try to update")

        mock_client.update_evaluator.assert_not_called()

    def test_update_evaluator_no_changes_fails(self, mock_client):
        """Test update fails with no changes."""
        with pytest.raises(ValueError, match="No updates provided"):
            update_evaluator(mock_client, evaluator_id="Custom.MyEval")

        mock_client.update_evaluator.assert_not_called()

    def test_update_evaluator_invalid_config(self, mock_client):
        """Test update fails with invalid config."""
        invalid_config = {"wrongKey": {}}

        with pytest.raises(ValueError, match="llmAsAJudge"):
            update_evaluator(mock_client, evaluator_id="Custom.MyEval", config=invalid_config)

        mock_client.update_evaluator.assert_not_called()

    def test_update_evaluator_instructions(self, mock_client, evaluator_details):
        """Test updating only instructions."""
        mock_client.get_evaluator.return_value = evaluator_details
        mock_client.update_evaluator.return_value = {"status": "success"}

        result = update_evaluator_instructions(
            mock_client, evaluator_id="Custom.MyEval", new_instructions="New instructions here"
        )

        assert result["status"] == "success"
        # Verify get was called
        mock_client.get_evaluator.assert_called_once_with(evaluator_id="Custom.MyEval")
        # Verify update was called with modified config
        call_args = mock_client.update_evaluator.call_args
        updated_config = call_args.kwargs["config"]
        assert updated_config["llmAsAJudge"]["instructions"] == "New instructions here"

    def test_update_evaluator_instructions_strips_whitespace(self, mock_client, evaluator_details):
        """Test instruction update strips whitespace."""
        mock_client.get_evaluator.return_value = evaluator_details
        mock_client.update_evaluator.return_value = {"status": "success"}

        update_evaluator_instructions(
            mock_client, evaluator_id="Custom.MyEval", new_instructions="  Padded instructions  "
        )

        call_args = mock_client.update_evaluator.call_args
        updated_config = call_args.kwargs["config"]
        assert updated_config["llmAsAJudge"]["instructions"] == "Padded instructions"

    def test_update_evaluator_instructions_invalid_config(self, mock_client):
        """Test instruction update fails if evaluator has invalid config."""
        invalid_details = {
            "evaluatorId": "Custom.MyEval",
            "evaluatorConfig": {},  # Missing llmAsAJudge
        }
        mock_client.get_evaluator.return_value = invalid_details

        with pytest.raises(ValueError, match="llmAsAJudge"):
            update_evaluator_instructions(mock_client, evaluator_id="Custom.MyEval", new_instructions="Test")


# =============================================================================
# Evaluator Deletion Tests
# =============================================================================


class TestEvaluatorDeletion:
    """Test evaluator deletion operations."""

    def test_delete_evaluator_success(self, mock_client):
        """Test successful deletion."""
        mock_client.delete_evaluator.return_value = None

        # Should not raise
        delete_evaluator(mock_client, "Custom.MyEval")

        mock_client.delete_evaluator.assert_called_once_with(evaluator_id="Custom.MyEval")

    @pytest.mark.parametrize(
        "builtin_id",
        [
            "Builtin.Helpfulness",
            "Builtin.Accuracy",
            "Builtin.Relevance",
        ],
    )
    def test_delete_evaluator_builtin_fails(self, mock_client, builtin_id):
        """Test deleting builtin evaluators fails."""
        with pytest.raises(ValueError, match="Built-in evaluators cannot be deleted"):
            delete_evaluator(mock_client, builtin_id)

        mock_client.delete_evaluator.assert_not_called()


# =============================================================================
# List and Query Tests
# =============================================================================


class TestListAndQuery:
    """Test list and query operations."""

    def test_list_evaluators_default(self, mock_client):
        """Test listing evaluators with default max results."""
        mock_client.list_evaluators.return_value = {
            "evaluators": [{"evaluatorId": "Builtin.Helpfulness"}, {"evaluatorId": "Custom.MyEval"}]
        }

        result = list_evaluators(mock_client)

        assert len(result["evaluators"]) == 2
        mock_client.list_evaluators.assert_called_once_with(max_results=50)

    @pytest.mark.parametrize("max_results", [10, 25, 100, 500])
    def test_list_evaluators_custom_max(self, mock_client, max_results):
        """Test listing evaluators with custom max results."""
        mock_client.list_evaluators.return_value = {"evaluators": []}

        list_evaluators(mock_client, max_results=max_results)

        mock_client.list_evaluators.assert_called_once_with(max_results=max_results)

    def test_get_evaluator(self, mock_client, evaluator_details):
        """Test getting evaluator details."""
        mock_client.get_evaluator.return_value = evaluator_details

        result = get_evaluator(mock_client, "Custom.MyEval")

        assert result["evaluatorId"] == "Custom.MyEval"
        assert result["level"] == "TRACE"
        mock_client.get_evaluator.assert_called_once_with(evaluator_id="Custom.MyEval")

    @pytest.mark.parametrize(
        "evaluator_id",
        [
            "Builtin.Helpfulness",
            "Custom.MyEval",
            "arn:aws:bedrock:::evaluator/Test",
        ],
    )
    def test_get_evaluator_various_ids(self, mock_client, evaluator_id):
        """Test getting evaluators with various ID formats."""
        mock_client.get_evaluator.return_value = {"evaluatorId": evaluator_id}

        result = get_evaluator(mock_client, evaluator_id)

        assert result["evaluatorId"] == evaluator_id
        mock_client.get_evaluator.assert_called_once_with(evaluator_id=evaluator_id)
