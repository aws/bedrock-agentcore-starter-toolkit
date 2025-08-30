"""Tests for Bedrock AgentCore runtime service integration."""

from unittest.mock import Mock, patch

import pytest
import requests

from bedrock_agentcore_starter_toolkit.services.runtime import (
    BedrockAgentCoreClient,
    HttpBedrockAgentCoreClient,
    LocalBedrockAgentCoreClient,
    _handle_streaming_response,
    generate_session_id,
)


class TestBedrockAgentCoreRuntime:
    """Test Bedrock AgentCore runtime service functionality."""

    def test_create_or_update_agent(self, mock_boto3_clients):
        """Test agent creation and update logic."""
        client = BedrockAgentCoreClient("us-west-2")

        # Test create agent (no existing agent_id)
        result = client.create_or_update_agent(
            agent_id=None,
            agent_name="test-agent",
            image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test:latest",
            execution_role_arn="arn:aws:iam::123456789012:role/TestRole",
        )

        # Verify create was called
        assert result["id"] == "test-agent-id"
        assert result["arn"] == "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
        mock_boto3_clients["bedrock_agentcore"].create_agent_runtime.assert_called_once()

        # Test update agent (existing agent_id)
        result = client.create_or_update_agent(
            agent_id="existing-agent-id",
            agent_name="test-agent",
            image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test:latest",
            execution_role_arn="arn:aws:iam::123456789012:role/TestRole",
        )

        # Verify update was called
        assert result["id"] == "existing-agent-id"
        assert result["arn"] == "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"
        mock_boto3_clients["bedrock_agentcore"].update_agent_runtime.assert_called_once()

    def test_wait_for_endpoint_ready(self, mock_boto3_clients):
        """Test endpoint readiness polling."""
        client = BedrockAgentCoreClient("us-west-2")

        # Test successful readiness
        endpoint_arn = client.wait_for_agent_endpoint_ready("test-agent-id")
        expected_arn = "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id/endpoint/default"
        assert endpoint_arn == expected_arn
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.assert_called()

    def test_wait_for_endpoint_ready_resource_not_found(self, mock_boto3_clients):
        """Test endpoint readiness with ResourceNotFoundException (should be handled gracefully)."""
        from botocore.exceptions import ClientError

        client = BedrockAgentCoreClient("us-west-2")

        # Mock ResourceNotFoundException followed by successful response
        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.side_effect = [
            ClientError(
                error_response={"Error": {"Code": "ResourceNotFoundException", "Message": "Endpoint not found"}},
                operation_name="GetAgentRuntimeEndpoint",
            ),
            {
                "status": "READY",
                "agentRuntimeEndpointArn": (
                    "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id/endpoint/default"
                ),
            },
        ]

        with patch("time.sleep"):  # Mock sleep to speed up test
            endpoint_arn = client.wait_for_agent_endpoint_ready("test-agent-id", max_wait=5)
            expected_arn = (
                "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id/endpoint/default"
            )
            assert endpoint_arn == expected_arn

    def test_invoke_endpoint(self, mock_boto3_clients):
        """Test agent invocation."""
        client = BedrockAgentCoreClient("us-west-2")

        response = client.invoke_endpoint(
            agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            payload='{"message": "Hello"}',
            session_id="test-session-123",
        )

        # Verify invocation was called correctly
        mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.assert_called_once_with(
            agentRuntimeArn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            qualifier="DEFAULT",
            runtimeSessionId="test-session-123",
            payload='{"message": "Hello"}',
        )

        # Verify response structure
        assert "response" in response
        assert response["response"] == [{"data": "test response"}]

    def test_api_error_handling(self, mock_boto3_clients):
        """Test handling of Bedrock AgentCore API errors."""
        client = BedrockAgentCoreClient("us-west-2")

        # Test basic error handling - simplified version
        assert client.region == "us-west-2"
        assert hasattr(client, "client")
        assert hasattr(client, "dataplane_client")

    def test_generate_session_id(self):
        """Test session ID generation."""
        session_id = generate_session_id()
        assert isinstance(session_id, str)
        assert len(session_id) > 0

        # Test uniqueness
        session_id2 = generate_session_id()
        assert session_id != session_id2

    def test_client_initialization(self, mock_boto3_clients):
        """Test Bedrock AgentCore client initialization."""
        client = BedrockAgentCoreClient("us-west-2")
        assert client.region == "us-west-2"
        assert client.client is not None
        assert client.dataplane_client is not None

    def test_create_agent_with_optional_configs(self, mock_boto3_clients):
        """Test create agent with network and authorizer configs."""
        client = BedrockAgentCoreClient("us-west-2")

        network_config = {"networkMode": "PRIVATE"}
        authorizer_config = {"type": "IAM"}
        protocol_config = {"serverProtocol": "MCP"}
        env_vars = {"ENV1": "HELLO", "ENV2": "WORLD"}

        result = client.create_agent(
            agent_name="test-agent",
            image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test:latest",
            execution_role_arn="arn:aws:iam::123456789012:role/TestRole",
            network_config=network_config,
            authorizer_config=authorizer_config,
            protocol_config=protocol_config,
            env_vars=env_vars,
        )

        assert result["id"] == "test-agent-id"
        assert result["arn"] == "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"

        # Verify the call included optional configs
        call_args = mock_boto3_clients["bedrock_agentcore"].create_agent_runtime.call_args[1]
        assert call_args["networkConfiguration"] == network_config
        assert call_args["authorizerConfiguration"] == authorizer_config
        assert call_args["protocolConfiguration"] == protocol_config
        assert call_args["environmentVariables"] == env_vars

    def test_create_agent_error_handling(self, mock_boto3_clients):
        """Test create agent error handling."""
        client = BedrockAgentCoreClient("us-west-2")

        # Mock an exception
        mock_boto3_clients["bedrock_agentcore"].create_agent_runtime.side_effect = Exception("API Error")

        try:
            client.create_agent(
                agent_name="test-agent",
                image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test:latest",
                execution_role_arn="arn:aws:iam::123456789012:role/TestRole",
            )
            raise AssertionError("Expected exception")
        except Exception as e:
            assert "API Error" in str(e)

    def test_update_agent_with_optional_configs(self, mock_boto3_clients):
        """Test update agent with network and authorizer configs."""
        client = BedrockAgentCoreClient("us-west-2")

        network_config = {"networkMode": "PRIVATE"}
        authorizer_config = {"type": "IAM"}
        protocol_config = {"serverProtocol": "MCP"}
        env_vars = {"ENV1": "HELLO", "ENV2": "WORLD"}

        result = client.update_agent(
            agent_id="existing-agent-id",
            image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test:latest",
            execution_role_arn="arn:aws:iam::123456789012:role/TestRole",
            network_config=network_config,
            authorizer_config=authorizer_config,
            protocol_config=protocol_config,
            env_vars=env_vars,
        )

        assert result["id"] == "existing-agent-id"
        assert result["arn"] == "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id"

        # Verify the call included optional configs
        call_args = mock_boto3_clients["bedrock_agentcore"].update_agent_runtime.call_args[1]
        assert call_args["networkConfiguration"] == network_config
        assert call_args["authorizerConfiguration"] == authorizer_config
        assert call_args["protocolConfiguration"] == protocol_config
        assert call_args["environmentVariables"] == env_vars

    def test_update_agent_error_handling(self, mock_boto3_clients):
        """Test update agent error handling."""
        client = BedrockAgentCoreClient("us-west-2")

        # Mock an exception
        mock_boto3_clients["bedrock_agentcore"].update_agent_runtime.side_effect = Exception("Update Error")

        try:
            client.update_agent(
                agent_id="existing-agent-id",
                image_uri="123456789012.dkr.ecr.us-west-2.amazonaws.com/test:latest",
                execution_role_arn="arn:aws:iam::123456789012:role/TestRole",
            )
            raise AssertionError("Expected exception")
        except Exception as e:
            assert "Update Error" in str(e)

    def test_get_agent_runtime(self, mock_boto3_clients):
        """Test get agent runtime."""
        client = BedrockAgentCoreClient("us-west-2")

        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.return_value = {
            "agentRuntimeId": "test-agent-id",
            "status": "READY",
        }

        result = client.get_agent_runtime("test-agent-id")
        assert result["agentRuntimeId"] == "test-agent-id"
        assert result["status"] == "READY"

        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime.assert_called_once_with(
            agentRuntimeId="test-agent-id"
        )

    def test_get_agent_runtime_endpoint(self, mock_boto3_clients):
        """Test get agent runtime endpoint."""
        client = BedrockAgentCoreClient("us-west-2")

        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.return_value = {
            "agentRuntimeEndpointArn": (
                "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id/endpoint/default"
            ),
            "status": "READY",
        }

        result = client.get_agent_runtime_endpoint("test-agent-id", "DEFAULT")
        assert "agentRuntimeEndpointArn" in result
        assert result["status"] == "READY"

        mock_boto3_clients["bedrock_agentcore"].get_agent_runtime_endpoint.assert_called_once_with(
            agentRuntimeId="test-agent-id", endpointName="DEFAULT"
        )

    def test_invoke_endpoint_with_events_error(self, mock_boto3_clients):
        """Test invoke endpoint with events processing error."""
        client = BedrockAgentCoreClient("us-west-2")

        # Mock response that will cause an error when iterating events
        mock_response = {"response": Exception("Event processing error"), "contentType": "application/json"}
        mock_boto3_clients["bedrock_agentcore"].invoke_agent_runtime.return_value = mock_response

        response = client.invoke_endpoint(
            agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-agent-id",
            payload='{"message": "Hello"}',
            session_id="test-session-123",
        )

        # Should handle the error gracefully
        assert "response" in response
        assert len(response["response"]) == 1
        assert "Error reading EventStream" in response["response"][0]


class TestHttpBedrockAgentCoreClient:
    """Test HttpBedrockAgentCoreClient functionality."""

    def test_invoke_endpoint_success(self):
        """Test successful endpoint invocation with bearer token."""
        client = HttpBedrockAgentCoreClient("us-west-2")

        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"data: response content\n\n"
        mock_response.text = "data: response content\n\n"
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {"content-type": "application/json"}

        with patch("requests.post", return_value=mock_response) as mock_post:
            result = client.invoke_endpoint(
                agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-id",
                payload='{"message": "hello"}',  # JSON string as it comes from invoke_bedrock_agentcore
                session_id="test-session-123",
                bearer_token="test-bearer-token",
            )

            # Verify request was made correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args

            # Check URL
            expected_url = "https://bedrock-agentcore.us-west-2.amazonaws.com/runtimes/arn%3Aaws%3Abedrock_agentcore%3Aus-west-2%3A123456789012%3Aagent-runtime%2Ftest-id/invocations"
            assert call_args[0][0] == expected_url

            # Check headers
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer test-bearer-token"
            assert headers["Content-Type"] == "application/json"
            assert headers["X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"] == "test-session-123"

            # Check payload - should now send the payload directly, not wrapped
            body = call_args[1]["json"]
            assert body == {"message": "hello"}

            # Check query params
            params = call_args[1]["params"]
            assert params["qualifier"] == "DEFAULT"

            # Check timeout
            assert call_args[1]["timeout"] == 900

            # Verify response
            assert result["response"] == "data: response content\n\n"

    def test_invoke_endpoint_with_custom_qualifier(self):
        """Test invocation with custom endpoint qualifier."""
        client = HttpBedrockAgentCoreClient("us-east-1")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test content"
        mock_response.text = "test content"
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {"content-type": "application/json"}

        with patch("requests.post", return_value=mock_response) as mock_post:
            client.invoke_endpoint(
                agent_arn="arn:aws:bedrock_agentcore:us-east-1:123456789012:agent-runtime/test-id",
                payload='"test payload"',  # JSON string as it would come from invoke_bedrock_agentcore
                session_id="session-456",
                bearer_token="token-123",
                endpoint_name="CUSTOM",
            )

            # Verify custom qualifier was used
            call_args = mock_post.call_args
            params = call_args[1]["params"]
            assert params["qualifier"] == "CUSTOM"

    def test_invoke_endpoint_http_error(self):
        """Test handling of HTTP errors."""
        client = HttpBedrockAgentCoreClient("us-west-2")

        # Mock HTTP error response
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(requests.exceptions.HTTPError):
                client.invoke_endpoint(
                    agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/nonexistent",
                    payload='{"test": "data"}',
                    session_id="session-123",
                    bearer_token="token-456",
                )

    def test_invoke_endpoint_connection_error(self):
        """Test handling of connection errors."""
        client = HttpBedrockAgentCoreClient("us-west-2")

        with patch("requests.post", side_effect=requests.exceptions.ConnectionError("Connection failed")):
            with pytest.raises(requests.exceptions.ConnectionError):
                client.invoke_endpoint(
                    agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-id",
                    payload='{"test": "data"}',
                    session_id="session-123",
                    bearer_token="token-456",
                )

    def test_invoke_endpoint_timeout(self):
        """Test handling of request timeout."""
        client = HttpBedrockAgentCoreClient("us-west-2")

        with patch("requests.post", side_effect=requests.exceptions.Timeout("Request timed out")):
            with pytest.raises(requests.exceptions.Timeout):
                client.invoke_endpoint(
                    agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-id",
                    payload='{"test": "data"}',
                    session_id="session-123",
                    bearer_token="token-456",
                )

    def test_invoke_endpoint_empty_response(self):
        """Test handling of empty response."""
        client = HttpBedrockAgentCoreClient("us-west-2")

        # Mock empty response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b""  # Empty content
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {"content-type": "application/json"}

        with patch("requests.post", return_value=mock_response):
            with pytest.raises(ValueError, match="Empty response from agent endpoint"):
                client.invoke_endpoint(
                    agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-id",
                    payload='{"test": "data"}',
                    session_id="session-123",
                    bearer_token="token-456",
                )

    def test_url_encoding_special_characters(self):
        """Test proper URL encoding of agent ARN with special characters."""
        client = HttpBedrockAgentCoreClient("us-west-2")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test"
        mock_response.text = "test"
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {"content-type": "application/json"}

        with patch("requests.post", return_value=mock_response) as mock_post:
            # ARN with special characters that need encoding
            complex_arn = "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-id:with:colons"

            client.invoke_endpoint(
                agent_arn=complex_arn, payload='{"test": "data"}', session_id="session-123", bearer_token="token-456"
            )

            # Verify URL encoding
            call_args = mock_post.call_args
            url = call_args[0][0]
            # Colons should be encoded as %3A
            assert "%3A" in url
            assert "with%3Acolons" in url

    def test_payload_types(self):
        """Test different payload types are handled correctly."""
        client = HttpBedrockAgentCoreClient("us-west-2")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"response"
        mock_response.text = "response"
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {"content-type": "application/json"}

        # Test cases as JSON strings (as they come from invoke_bedrock_agentcore)
        test_cases = [
            ('{"message": "hello"}', {"message": "hello"}),  # Valid JSON dict
            ('"simple string"', "simple string"),  # Valid JSON string
            ('["list", "payload"]', ["list", "payload"]),  # Valid JSON list
            ("42", 42),  # Valid JSON number
            ("invalid json string", {"payload": "invalid json string"}),  # Invalid JSON - fallback
        ]

        with patch("requests.post", return_value=mock_response) as mock_post:
            for payload_input, expected_body in test_cases:
                client.invoke_endpoint(
                    agent_arn="arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-id",
                    payload=payload_input,
                    session_id="session-123",
                    bearer_token="token-456",
                )

                # Verify payload was parsed and sent correctly
                call_args = mock_post.call_args
                body = call_args[1]["json"]
                assert body == expected_body

                mock_post.reset_mock()


class TestLocalBedrockAgentCoreClient:
    """Test LocalBedrockAgentCoreClient functionality."""

    def test_initialization(self):
        """Test LocalBedrockAgentCoreClient initialization."""
        endpoint = "http://localhost:8080"
        client = LocalBedrockAgentCoreClient(endpoint)

        assert client.endpoint == endpoint

    def test_invoke_endpoint_success(self):
        """Test successful endpoint invocation."""
        client = LocalBedrockAgentCoreClient("http://localhost:8080")

        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"test response content"
        mock_response.text = "test response content"
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {"content-type": "application/json"}

        with (
            patch("requests.post", return_value=mock_response) as mock_post,
            patch(
                "bedrock_agentcore_starter_toolkit.services.runtime._handle_http_response",
                return_value={"response": "test response"},
            ) as mock_handle,
        ):
            result = client.invoke_endpoint(
                session_id="test-session-123", payload='{"message": "hello"}', workload_access_token="test-token-456"
            )

            # Verify request was made correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args

            # Check URL
            expected_url = "http://localhost:8080/invocations"
            assert call_args[0][0] == expected_url

            # Check headers - need to import the constants
            from bedrock_agentcore.runtime.models import ACCESS_TOKEN_HEADER, SESSION_HEADER

            headers = call_args[1]["headers"]
            assert headers["Content-Type"] == "application/json"
            assert headers[ACCESS_TOKEN_HEADER] == "test-token-456"
            assert headers[SESSION_HEADER] == "test-session-123"

            # Check payload
            body = call_args[1]["json"]
            assert body == {"message": "hello"}

            # Check timeout
            assert call_args[1]["timeout"] == 900
            assert call_args[1]["stream"] is True

            # Verify response handling
            mock_handle.assert_called_once_with(mock_response)
            assert result == {"response": "test response"}

    def test_invoke_endpoint_with_non_json_payload(self):
        """Test invocation with non-JSON payload."""
        client = LocalBedrockAgentCoreClient("http://localhost:9090")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = b"response"
        mock_response.text = "response"
        mock_response.raise_for_status.return_value = None
        mock_response.headers = {"content-type": "application/json"}

        with (
            patch("requests.post", return_value=mock_response) as mock_post,
            patch(
                "bedrock_agentcore_starter_toolkit.services.runtime._handle_http_response",
                return_value={"response": "wrapped"},
            ),
        ):
            # Test with invalid JSON string
            client.invoke_endpoint(
                session_id="session-456", payload="invalid json string", workload_access_token="token-123"
            )

            # Verify payload was wrapped
            call_args = mock_post.call_args
            body = call_args[1]["json"]
            assert body == {"payload": "invalid json string"}


class TestHandleStreamingResponse:
    """Test _handle_streaming_response functionality."""

    def test_handle_streaming_response_with_data_lines(self):
        """Test streaming response with data: prefixed lines."""
        # Mock response object with JSON data chunks
        mock_response = Mock()
        mock_response.iter_lines.return_value = [
            b'data: "Hello from agent"',
            b'data: "This is a streaming response"',
            b'data: "Final chunk"',
        ]

        # Mock console to capture print calls
        with patch("bedrock_agentcore_starter_toolkit.services.runtime.console") as mock_console:
            result = _handle_streaming_response(mock_response)

            # Verify result structure - function returns empty dict for streaming
            assert result == {}

            # Verify console.print was called for each JSON chunk + final newline
            assert mock_console.print.call_count == 4  # 3 chunks + 1 final newline
            mock_console.print.assert_any_call("Hello from agent", end="", style="bold cyan")
            mock_console.print.assert_any_call("This is a streaming response", end="", style="bold cyan")
            mock_console.print.assert_any_call("Final chunk", end="", style="bold cyan")
            mock_console.print.assert_any_call()  # Final newline call


class TestHandleAwsResponseUnicode:
    """Test _handle_aws_response functionality with Unicode/multibyte character support."""

    def test_handle_aws_response_with_byte_strings_chinese(self):
        """Test handling of Chinese characters in byte string responses."""
        from bedrock_agentcore_starter_toolkit.services.runtime import _handle_aws_response
        
        # Chinese text: "你好世界" (Hello World)
        chinese_text = "你好世界"
        chinese_bytes = chinese_text.encode('utf-8')
        
        response = {
            "contentType": "application/json",
            "response": [chinese_bytes]
        }
        
        result = _handle_aws_response(response)
        
        # Verify the byte string was properly decoded
        assert "response" in result
        assert len(result["response"]) == 1
        assert result["response"][0] == chinese_text

    def test_handle_aws_response_with_byte_strings_japanese(self):
        """Test handling of Japanese characters in byte string responses."""
        from bedrock_agentcore_starter_toolkit.services.runtime import _handle_aws_response
        
        # Japanese text: "こんにちは" (Hello)
        japanese_text = "こんにちは"
        japanese_bytes = japanese_text.encode('utf-8')
        
        response = {
            "contentType": "application/json",
            "response": [japanese_bytes]
        }
        
        result = _handle_aws_response(response)
        
        # Verify the byte string was properly decoded
        assert "response" in result
        assert len(result["response"]) == 1
        assert result["response"][0] == japanese_text

    def test_handle_aws_response_with_byte_strings_korean(self):
        """Test handling of Korean characters in byte string responses."""
        from bedrock_agentcore_starter_toolkit.services.runtime import _handle_aws_response
        
        # Korean text: "안녕하세요" (Hello)
        korean_text = "안녕하세요"
        korean_bytes = korean_text.encode('utf-8')
        
        response = {
            "contentType": "application/json",
            "response": [korean_bytes]
        }
        
        result = _handle_aws_response(response)
        
        # Verify the byte string was properly decoded
        assert "response" in result
        assert len(result["response"]) == 1
        assert result["response"][0] == korean_text

    def test_handle_aws_response_with_json_byte_strings(self):
        """Test handling of JSON content in byte strings."""
        import json
        from bedrock_agentcore_starter_toolkit.services.runtime import _handle_aws_response
        
        # JSON with Chinese characters
        json_data = {"message": "你好世界", "status": "success"}
        json_bytes = json.dumps(json_data, ensure_ascii=False).encode('utf-8')
        
        response = {
            "contentType": "application/json",
            "response": [json_bytes]
        }
        
        result = _handle_aws_response(response)
        
        # Verify the JSON was properly parsed
        assert "response" in result
        assert len(result["response"]) == 1
        assert result["response"][0] == json_data

    def test_handle_aws_response_with_mixed_event_types(self):
        """Test handling of mixed event types (bytes, strings, dicts)."""
        import json
        from bedrock_agentcore_starter_toolkit.services.runtime import _handle_aws_response
        
        # Mix of different event types
        chinese_bytes = "你好".encode('utf-8')
        json_bytes = '{"key": "值"}'.encode('utf-8')
        string_event = "regular string"
        dict_event = {"existing": "dict"}
        
        response = {
            "contentType": "application/json",
            "response": [chinese_bytes, json_bytes, string_event, dict_event]
        }
        
        result = _handle_aws_response(response)
        
        # Verify all events were handled correctly
        assert "response" in result
        assert len(result["response"]) == 4
        assert result["response"][0] == "你好"  # Decoded Chinese
        assert result["response"][1] == {"key": "值"}  # Parsed JSON with Chinese
        assert result["response"][2] == "regular string"  # Unchanged string
        assert result["response"][3] == {"existing": "dict"}  # Unchanged dict

    def test_handle_aws_response_with_invalid_json_bytes(self):
        """Test handling of byte strings that contain invalid JSON."""
        from bedrock_agentcore_starter_toolkit.services.runtime import _handle_aws_response
        
        # Invalid JSON with Chinese characters
        invalid_json_text = "你好世界 - this is not valid JSON"
        invalid_json_bytes = invalid_json_text.encode('utf-8')
        
        response = {
            "contentType": "application/json",
            "response": [invalid_json_bytes]
        }
        
        result = _handle_aws_response(response)
        
        # Verify it falls back to plain text
        assert "response" in result
        assert len(result["response"]) == 1
        assert result["response"][0] == invalid_json_text

    def test_handle_aws_response_backward_compatibility(self):
        """Test that existing string and dict events still work (backward compatibility)."""
        from bedrock_agentcore_starter_toolkit.services.runtime import _handle_aws_response
        
        response = {
            "contentType": "application/json",
            "response": [
                "existing string event",
                {"existing": "dict event"},
                ["existing", "list", "event"]
            ]
        }
        
        result = _handle_aws_response(response)
        
        # Verify existing behavior is unchanged
        assert "response" in result
        assert len(result["response"]) == 3
        assert result["response"][0] == "existing string event"
        assert result["response"][1] == {"existing": "dict event"}
        assert result["response"][2] == ["existing", "list", "event"]

    def test_handle_aws_response_streaming_unchanged(self):
        """Test that streaming responses are not affected by the Unicode fix."""
        from bedrock_agentcore_starter_toolkit.services.runtime import _handle_aws_response
        
        # Mock streaming response
        mock_stream_response = Mock()
        
        response = {
            "contentType": "text/event-stream",
            "response": mock_stream_response
        }
        
        with patch("bedrock_agentcore_starter_toolkit.services.runtime._handle_streaming_response") as mock_handler:
            mock_handler.return_value = {"streaming": "result"}
            
            result = _handle_aws_response(response)
            
            # Verify streaming handler was called
            mock_handler.assert_called_once_with(mock_stream_response)
            assert result == {"streaming": "result"}

    def test_handle_aws_response_error_handling(self):
        """Test error handling in _handle_aws_response with Unicode content."""
        from bedrock_agentcore_starter_toolkit.services.runtime import _handle_aws_response
        
        # Response that will cause an error during iteration
        response = {
            "contentType": "application/json",
            "response": Exception("Processing error")
        }
        
        result = _handle_aws_response(response)
        
        # Verify error is handled gracefully
        assert "response" in result
        assert len(result["response"]) == 1
        assert "Error reading EventStream" in result["response"][0]

    def test_handle_aws_response_empty_response(self):
        """Test handling of empty response list."""
        from bedrock_agentcore_starter_toolkit.services.runtime import _handle_aws_response
        
        response = {
            "contentType": "application/json",
            "response": []
        }
        
        result = _handle_aws_response(response)
        
        # Verify empty response is handled correctly
        assert "response" in result
        assert result["response"] == []

    def test_handle_aws_response_emoji_and_special_chars(self):
        """Test handling of emojis and special Unicode characters."""
        from bedrock_agentcore_starter_toolkit.services.runtime import _handle_aws_response
        
        # Text with emojis and special characters
        emoji_text = "Hello 👋 World 🌍 测试 🧪"
        emoji_bytes = emoji_text.encode('utf-8')
        
        response = {
            "contentType": "application/json",
            "response": [emoji_bytes]
        }
        
        result = _handle_aws_response(response)
        
        # Verify emojis and special characters are preserved
        assert "response" in result
        assert len(result["response"]) == 1
        assert result["response"][0] == emoji_text
