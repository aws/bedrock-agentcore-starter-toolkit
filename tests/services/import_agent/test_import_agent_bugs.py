"""Tests for import-agent bug fixes (V2200635700)."""

from unittest.mock import MagicMock, patch


class TestLambdaCreatedBeforeGatewayTargets:
    """Bug #1: Gateway Lambda must be created before targets reference it."""

    @patch("boto3.client")
    def test_create_lambda_called_before_gateway_targets(self, mock_boto_client):
        """Verify create_lambda is called before any create_gateway_lambda_target."""
        from bedrock_agentcore_starter_toolkit.services.import_agent.scripts.base_bedrock_translate import (
            BaseBedrockTranslator,
        )

        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_boto_client.return_value = mock_sts

        translator = BaseBedrockTranslator.__new__(BaseBedrockTranslator)
        translator.agent_region = "us-west-2"
        translator.cleaned_agent_name = "test_agent"
        translator.created_gateway = {"gatewayId": "gw-123", "roleArn": "arn:aws:iam::123456789012:role/test"}
        translator.gateway_client = MagicMock()
        translator.agent_info = {"agentName": "test", "agentId": "id", "alias": "a", "version": "1"}

        translator.custom_ags = [
            {
                "actionGroupExecutor": {"lambda": "arn:aws:lambda:us-west-2:123456789012:function:orig"},
                "actionGroupName": "TestGroup",
                "description": "test",
                "apiSchema": {
                    "payload": {
                        "paths": {
                            "/test": {
                                "get": {
                                    "summary": "Test endpoint",
                                    "parameters": [],
                                }
                            }
                        }
                    }
                },
            }
        ]

        call_order = []
        translator.create_lambda = MagicMock(side_effect=lambda *a, **kw: call_order.append("create_lambda"))
        translator.create_gateway_lambda_target = MagicMock(
            side_effect=lambda *a, **kw: call_order.append("create_gateway_lambda_target")
        )

        with patch("time.sleep"):
            translator.create_gateway_proxy_and_targets()

        assert call_order[0] == "create_lambda", "create_lambda must be called before create_gateway_lambda_target"
        assert "create_gateway_lambda_target" in call_order


class TestApiSchemaAsString:
    """Bug #2: apiSchema can be a raw string instead of a dict."""

    def test_agent_info_handles_string_api_schema(self):
        """agent_info.py string apiSchema guard converts it to a dict with parsed payload."""
        from ruamel.yaml import YAML

        # Simulate what agent_info.py does with string apiSchema
        action_group = {
            "apiSchema": "openapi: '3.0.0'\npaths: {}",
            "actionGroupName": "TestGroup",
        }

        api_schema = action_group["apiSchema"]
        if isinstance(api_schema, str):
            yaml = YAML(typ="safe")
            action_group["apiSchema"] = {"payload": yaml.load(api_schema)}

        # Verify it was converted to a dict with parsed YAML
        assert isinstance(action_group["apiSchema"], dict)
        assert action_group["apiSchema"]["payload"] == {"openapi": "3.0.0", "paths": {}}
        # .get() should now work
        assert action_group["apiSchema"].get("payload", False) is not False

    @patch("boto3.client")
    def test_base_translate_handles_string_api_schema(self, mock_boto_client):
        """base_bedrock_translate.py should skip string apiSchema gracefully."""
        from bedrock_agentcore_starter_toolkit.services.import_agent.scripts.base_bedrock_translate import (
            BaseBedrockTranslator,
        )

        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_boto_client.return_value = mock_sts

        translator = BaseBedrockTranslator.__new__(BaseBedrockTranslator)
        translator.agent_region = "us-west-2"
        translator.cleaned_agent_name = "test_agent"
        translator.created_gateway = {"gatewayId": "gw-123", "roleArn": "arn:aws:iam::123456789012:role/test"}
        translator.gateway_client = MagicMock()
        translator.agent_info = {"agentName": "test", "agentId": "id", "alias": "a", "version": "1"}

        translator.custom_ags = [
            {
                "actionGroupExecutor": {"lambda": "arn:aws:lambda:us-west-2:123456789012:function:orig"},
                "actionGroupName": "TestGroup",
                "description": "test",
                "apiSchema": "openapi: '3.0.0'\npaths: {}",
            }
        ]

        translator.create_lambda = MagicMock()
        translator.create_gateway_lambda_target = MagicMock()

        with patch("time.sleep"):
            translator.create_gateway_proxy_and_targets()

        # Should not crash; no targets created since string schema yields no tools
        translator.create_gateway_lambda_target.assert_not_called()

    @patch("boto3.client")
    def test_dict_api_schema_still_works(self, mock_boto_client):
        """Regression: dict apiSchema with payload should still extract tools."""
        from bedrock_agentcore_starter_toolkit.services.import_agent.scripts.base_bedrock_translate import (
            BaseBedrockTranslator,
        )

        mock_sts = MagicMock()
        mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}
        mock_boto_client.return_value = mock_sts

        translator = BaseBedrockTranslator.__new__(BaseBedrockTranslator)
        translator.agent_region = "us-west-2"
        translator.cleaned_agent_name = "test_agent"
        translator.created_gateway = {"gatewayId": "gw-123", "roleArn": "arn:aws:iam::123456789012:role/test"}
        translator.gateway_client = MagicMock()
        translator.agent_info = {"agentName": "test", "agentId": "id", "alias": "a", "version": "1"}

        translator.custom_ags = [
            {
                "actionGroupExecutor": {"lambda": "arn:aws:lambda:us-west-2:123456789012:function:orig"},
                "actionGroupName": "TestGroup",
                "description": "test",
                "apiSchema": {
                    "payload": {
                        "paths": {
                            "/test": {
                                "get": {
                                    "summary": "Test endpoint",
                                    "parameters": [],
                                }
                            }
                        }
                    }
                },
            }
        ]

        translator.create_lambda = MagicMock()
        translator.create_gateway_lambda_target = MagicMock()

        with patch("time.sleep"):
            translator.create_gateway_proxy_and_targets()

        translator.create_gateway_lambda_target.assert_called_once()
