"""Tests for lambda_utils module."""

import io
import zipfile
from unittest.mock import Mock

import pytest

from bedrock_agentcore_starter_toolkit.utils.lambda_utils import create_lambda_function


class TestCreateLambdaFunction:
    """Test suite for create_lambda_function."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock boto3 session."""
        session = Mock()
        session.client = Mock()
        return session

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock()

    @pytest.fixture
    def sample_lambda_code(self):
        """Sample Lambda function code."""
        return """
def lambda_handler(event, context):
    return {'statusCode': 200, 'body': 'Hello World'}
"""

    def test_create_lambda_function_success(self, mock_session, mock_logger, sample_lambda_code):
        """Test successful Lambda function creation with new role and function."""
        # Setup mocks
        mock_lambda = Mock()
        mock_iam = Mock()

        mock_session.client.side_effect = lambda service: mock_lambda if service == "lambda" else mock_iam

        # Mock IAM role creation
        mock_iam.create_role.return_value = {"Role": {"Arn": "arn:aws:iam::123456789012:role/TestRole"}}
        mock_iam.attach_role_policy.return_value = {}

        # Mock Lambda function creation
        mock_lambda.create_function.return_value = {
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:TestFunction"
        }
        mock_lambda.add_permission.return_value = {}

        # Execute
        result = create_lambda_function(
            session=mock_session,
            logger=mock_logger,
            function_name="TestFunction",
            lambda_code=sample_lambda_code,
            runtime="python3.13",
            handler="lambda_function.lambda_handler",
            gateway_role_arn="arn:aws:iam::123456789012:role/GatewayRole",
            description="Test Lambda function",
        )

        # Verify
        assert result == "arn:aws:lambda:us-east-1:123456789012:function:TestFunction"
        mock_iam.create_role.assert_called_once()
        mock_iam.attach_role_policy.assert_called_once()
        mock_lambda.create_function.assert_called_once()
        mock_lambda.add_permission.assert_called_once()

    def test_create_lambda_function_with_existing_role(self, mock_session, mock_logger, sample_lambda_code):
        """Test Lambda function creation when IAM role already exists."""
        # Setup mocks
        mock_lambda = Mock()
        mock_iam = Mock()

        mock_session.client.side_effect = lambda service: mock_lambda if service == "lambda" else mock_iam

        # Create the exception class first
        EntityAlreadyExistsException = type("EntityAlreadyExistsException", (Exception,), {})
        mock_iam.exceptions.EntityAlreadyExistsException = EntityAlreadyExistsException

        # Mock IAM role already exists
        mock_iam.create_role.side_effect = EntityAlreadyExistsException(
            {"Error": {"Code": "EntityAlreadyExists", "Message": "Role already exists"}}, "CreateRole"
        )
        mock_iam.get_role.return_value = {"Role": {"Arn": "arn:aws:iam::123456789012:role/TestFunctionRole"}}

        # Mock Lambda function creation
        mock_lambda.create_function.return_value = {
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:TestFunction"
        }
        mock_lambda.add_permission.return_value = {}

        # Execute
        result = create_lambda_function(
            session=mock_session,
            logger=mock_logger,
            function_name="TestFunction",
            lambda_code=sample_lambda_code,
            runtime="python3.13",
            handler="lambda_function.lambda_handler",
            gateway_role_arn="arn:aws:iam::123456789012:role/GatewayRole",
        )

        # Verify
        assert result == "arn:aws:lambda:us-east-1:123456789012:function:TestFunction"
        mock_iam.get_role.assert_called_once_with(RoleName="TestFunctionRole")
        mock_lambda.create_function.assert_called_once()

    def test_create_lambda_function_already_exists(self, mock_session, mock_logger, sample_lambda_code):
        """Test when Lambda function already exists."""
        # Setup mocks
        mock_lambda = Mock()
        mock_iam = Mock()

        mock_session.client.side_effect = lambda service: mock_lambda if service == "lambda" else mock_iam

        # Mock IAM role creation
        mock_iam.create_role.return_value = {"Role": {"Arn": "arn:aws:iam::123456789012:role/TestFunctionRole"}}
        mock_iam.attach_role_policy.return_value = {}

        # Create the exception class first
        ResourceConflictException = type("ResourceConflictException", (Exception,), {})
        mock_lambda.exceptions.ResourceConflictException = ResourceConflictException

        # Mock Lambda function already exists
        mock_lambda.create_function.side_effect = ResourceConflictException(
            {"Error": {"Code": "ResourceConflictException", "Message": "Function already exists"}}, "CreateFunction"
        )
        mock_lambda.get_function.return_value = {
            "Configuration": {"FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:TestFunction"}
        }

        # Execute
        result = create_lambda_function(
            session=mock_session,
            logger=mock_logger,
            function_name="TestFunction",
            lambda_code=sample_lambda_code,
            runtime="python3.13",
            handler="lambda_function.lambda_handler",
            gateway_role_arn="arn:aws:iam::123456789012:role/GatewayRole",
        )

        # Verify
        assert result == "arn:aws:lambda:us-east-1:123456789012:function:TestFunction"
        mock_lambda.get_function.assert_called_once_with(FunctionName="TestFunction")

    def test_create_lambda_function_zip_creation(self, mock_session, mock_logger, sample_lambda_code):
        """Test that Lambda deployment package is created correctly."""
        # Setup mocks
        mock_lambda = Mock()
        mock_iam = Mock()

        mock_session.client.side_effect = lambda service: mock_lambda if service == "lambda" else mock_iam

        mock_iam.create_role.return_value = {"Role": {"Arn": "arn:aws:iam::123456789012:role/TestFunctionRole"}}
        mock_iam.attach_role_policy.return_value = {}

        # Capture the zip file content
        captured_zip = None

        def capture_zip(*args, **kwargs):
            nonlocal captured_zip
            captured_zip = kwargs.get("Code", {}).get("ZipFile")
            return {"FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:TestFunction"}

        mock_lambda.create_function.side_effect = capture_zip
        mock_lambda.add_permission.return_value = {}

        # Execute
        create_lambda_function(
            session=mock_session,
            logger=mock_logger,
            function_name="TestFunction",
            lambda_code=sample_lambda_code,
            runtime="python3.13",
            handler="lambda_function.lambda_handler",
            gateway_role_arn="arn:aws:iam::123456789012:role/GatewayRole",
        )

        # Verify zip contents
        assert captured_zip is not None
        zip_buffer = io.BytesIO(captured_zip)
        with zipfile.ZipFile(zip_buffer, "r") as zip_file:
            assert "lambda_function.py" in zip_file.namelist()
            assert zip_file.read("lambda_function.py").decode() == sample_lambda_code

    def test_create_lambda_function_iam_policy_attachment(self, mock_session, mock_logger, sample_lambda_code):
        """Test that correct IAM policy is attached to Lambda execution role."""
        # Setup mocks
        mock_lambda = Mock()
        mock_iam = Mock()

        mock_session.client.side_effect = lambda service: mock_lambda if service == "lambda" else mock_iam

        mock_iam.create_role.return_value = {"Role": {"Arn": "arn:aws:iam::123456789012:role/TestFunctionRole"}}
        mock_iam.attach_role_policy.return_value = {}

        mock_lambda.create_function.return_value = {
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:TestFunction"
        }
        mock_lambda.add_permission.return_value = {}

        # Execute
        create_lambda_function(
            session=mock_session,
            logger=mock_logger,
            function_name="TestFunction",
            lambda_code=sample_lambda_code,
            runtime="python3.13",
            handler="lambda_function.lambda_handler",
            gateway_role_arn="arn:aws:iam::123456789012:role/GatewayRole",
        )

        # Verify IAM policy attachment
        mock_iam.attach_role_policy.assert_called_once_with(
            RoleName="TestFunctionRole",
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
        )

    def test_create_lambda_function_invoke_permission(self, mock_session, mock_logger, sample_lambda_code):
        """Test that Lambda invoke permission is added for gateway role."""
        # Setup mocks
        mock_lambda = Mock()
        mock_iam = Mock()

        mock_session.client.side_effect = lambda service: mock_lambda if service == "lambda" else mock_iam

        mock_iam.create_role.return_value = {"Role": {"Arn": "arn:aws:iam::123456789012:role/TestFunctionRole"}}
        mock_iam.attach_role_policy.return_value = {}

        mock_lambda.create_function.return_value = {
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:TestFunction"
        }
        mock_lambda.add_permission.return_value = {}

        gateway_role_arn = "arn:aws:iam::123456789012:role/GatewayRole"

        # Execute
        create_lambda_function(
            session=mock_session,
            logger=mock_logger,
            function_name="TestFunction",
            lambda_code=sample_lambda_code,
            runtime="python3.13",
            handler="lambda_function.lambda_handler",
            gateway_role_arn=gateway_role_arn,
        )

        # Verify Lambda permission
        mock_lambda.add_permission.assert_called_once_with(
            FunctionName="TestFunction",
            StatementId="AllowAgentCoreInvoke",
            Action="lambda:InvokeFunction",
            Principal=gateway_role_arn,
        )

    def test_create_lambda_function_with_custom_description(self, mock_session, mock_logger, sample_lambda_code):
        """Test Lambda function creation with custom description."""
        # Setup mocks
        mock_lambda = Mock()
        mock_iam = Mock()

        mock_session.client.side_effect = lambda service: mock_lambda if service == "lambda" else mock_iam

        mock_iam.create_role.return_value = {"Role": {"Arn": "arn:aws:iam::123456789012:role/TestFunctionRole"}}
        mock_iam.attach_role_policy.return_value = {}
        mock_lambda.create_function.return_value = {
            "FunctionArn": "arn:aws:lambda:us-east-1:123456789012:function:TestFunction"
        }
        mock_lambda.add_permission.return_value = {}

        custom_description = "Custom test description"

        # Execute
        create_lambda_function(
            session=mock_session,
            logger=mock_logger,
            function_name="TestFunction",
            lambda_code=sample_lambda_code,
            runtime="python3.13",
            handler="lambda_function.lambda_handler",
            gateway_role_arn="arn:aws:iam::123456789012:role/GatewayRole",
            description=custom_description,
        )

        # Verify description in create_function call
        call_args = mock_lambda.create_function.call_args
        assert call_args[1]["Description"] == custom_description
