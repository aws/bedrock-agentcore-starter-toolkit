"""Tests for Identity helper functions."""

import base64
import hashlib
import hmac
import json
from unittest.mock import Mock, patch

import pytest
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.operations.identity.helpers import (
    IdentityCognitoManager,
    _generate_password,
    _random_suffix,
    create_cognito_oauth_pool,
    ensure_identity_permissions,
    get_cognito_access_token,
    update_cognito_callback_urls,
)


class TestCreateCognitoOAuthPool:
    """Test create_cognito_oauth_pool function."""

    def test_create_pool_basic(self):
        """Test basic Cognito pool creation."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            # Mock responses
            mock_cognito.create_user_pool.return_value = {"UserPool": {"Id": "us-west-2_testpool123"}}
            mock_cognito.create_user_pool_domain.return_value = {}
            mock_cognito.create_user_pool_client.return_value = {
                "UserPoolClient": {"ClientId": "abc123", "ClientSecret": "xyz789"}
            }
            mock_cognito.admin_create_user.return_value = {}
            mock_cognito.admin_set_user_password.return_value = {}

            result = create_cognito_oauth_pool(base_name="TestPool", region="us-west-2", create_test_user=True)

            # Verify pool was created
            assert result["pool_id"] == "us-west-2_testpool123"
            assert result["client_id"] == "abc123"
            assert result["client_secret"] == "xyz789"
            assert result["region"] == "us-west-2"
            assert "username" in result
            assert "password" in result
            assert "discovery_url" in result
            assert "hosted_ui_url" in result

            # Verify boto3 calls
            mock_cognito.create_user_pool.assert_called_once()
            mock_cognito.create_user_pool_domain.assert_called_once()
            mock_cognito.create_user_pool_client.assert_called_once()
            mock_cognito.admin_create_user.assert_called_once()
            mock_cognito.admin_set_user_password.assert_called_once()

    def test_create_pool_with_callback_url(self):
        """Test pool creation with AgentCore callback URL."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            mock_cognito.create_user_pool.return_value = {"UserPool": {"Id": "us-west-2_testpool"}}
            mock_cognito.create_user_pool_domain.return_value = {}
            mock_cognito.create_user_pool_client.return_value = {
                "UserPoolClient": {"ClientId": "client123", "ClientSecret": "secret123"}
            }

            agentcore_url = "https://bedrock-agentcore.us-west-2.amazonaws.com/callback"
            # Use the result instead of just assigning it
            result = create_cognito_oauth_pool(
                base_name="TestPool",
                region="us-west-2",
                create_test_user=False,
                agentcore_callback_url=agentcore_url,
            )

            # Verify callback URL was included
            client_call_args = mock_cognito.create_user_pool_client.call_args[1]
            assert agentcore_url in client_call_args["CallbackURLs"]

            # Also verify the result contains expected values
            assert result["pool_id"] == "us-west-2_testpool"
            assert result["client_id"] == "client123"

    def test_create_pool_for_runtime_auth(self):
        """Test pool creation for runtime authentication (no client secret)."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            mock_cognito.create_user_pool.return_value = {"UserPool": {"Id": "us-west-2_testpool"}}
            mock_cognito.create_user_pool_domain.return_value = {}
            mock_cognito.create_user_pool_client.return_value = {
                "UserPoolClient": {"ClientId": "client123"}  # No secret
            }

            result = create_cognito_oauth_pool(
                base_name="RuntimePool", region="us-west-2", create_test_user=False, use_for_runtime_auth=True
            )

            # Verify no client secret in result
            assert "client_secret" not in result
            assert result["client_id"] == "client123"

            # Verify auth flows configured correctly
            client_call_args = mock_cognito.create_user_pool_client.call_args[1]
            assert "GenerateSecret" not in client_call_args
            assert "ALLOW_USER_PASSWORD_AUTH" in client_call_args["ExplicitAuthFlows"]

    def test_create_pool_for_identity_3lo(self):
        """Test pool creation for Identity 3LO (with client secret)."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            mock_cognito.create_user_pool.return_value = {"UserPool": {"Id": "us-west-2_testpool"}}
            mock_cognito.create_user_pool_domain.return_value = {}
            mock_cognito.create_user_pool_client.return_value = {
                "UserPoolClient": {"ClientId": "client123", "ClientSecret": "secret123"}
            }

            result = create_cognito_oauth_pool(
                base_name="Identity3LOPool", region="us-west-2", create_test_user=False, use_for_runtime_auth=False
            )

            # Verify client secret is present
            assert result["client_secret"] == "secret123"

            # Verify auth flows configured for 3LO
            client_call_args = mock_cognito.create_user_pool_client.call_args[1]
            assert client_call_args["GenerateSecret"] is True


class TestUpdateCognitoCallbackUrls:
    """Test update_cognito_callback_urls function."""

    def test_update_adds_new_url(self):
        """Test adding new callback URL to existing URLs."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            # Mock current client config
            mock_cognito.describe_user_pool_client.return_value = {
                "UserPoolClient": {
                    "CallbackURLs": ["https://existing.example.com/callback"],
                    "AllowedOAuthFlows": ["code"],
                    "AllowedOAuthScopes": ["openid"],
                    "SupportedIdentityProviders": ["COGNITO"],
                }
            }

            new_url = "https://bedrock-agentcore.us-west-2.amazonaws.com/callback"
            update_cognito_callback_urls(
                pool_id="us-west-2_testpool", client_id="client123", callback_url=new_url, region="us-west-2"
            )

            # Verify update was called with both URLs
            mock_cognito.update_user_pool_client.assert_called_once()
            update_args = mock_cognito.update_user_pool_client.call_args[1]
            assert set(update_args["CallbackURLs"]) == {
                "https://existing.example.com/callback",
                "https://bedrock-agentcore.us-west-2.amazonaws.com/callback",
            }

    def test_update_skips_duplicate_url(self):
        """Test that duplicate URL is not added (update is skipped)."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            existing_url = "https://bedrock-agentcore.us-west-2.amazonaws.com/callback"
            mock_cognito.describe_user_pool_client.return_value = {
                "UserPoolClient": {
                    "CallbackURLs": [existing_url],
                    "AllowedOAuthFlows": ["code"],
                    "AllowedOAuthScopes": ["openid"],
                    "SupportedIdentityProviders": ["COGNITO"],
                }
            }

            update_cognito_callback_urls(
                pool_id="us-west-2_testpool", client_id="client123", callback_url=existing_url, region="us-west-2"
            )

            # Verify update was NOT called since URL already exists
            mock_cognito.update_user_pool_client.assert_not_called()


class TestGetCognitoAccessToken:
    """Test get_cognito_access_token function."""

    def test_get_token_without_secret(self):
        """Test getting access token without client secret."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            mock_cognito.initiate_auth.return_value = {"AuthenticationResult": {"AccessToken": "test-access-token-123"}}

            token = get_cognito_access_token(
                pool_id="us-west-2_testpool",
                client_id="client123",
                username="testuser",
                password="Pass123!",
                region="us-west-2",
            )

            assert token == "test-access-token-123"

            # Verify auth parameters
            auth_call = mock_cognito.initiate_auth.call_args[1]
            assert auth_call["AuthFlow"] == "USER_PASSWORD_AUTH"
            assert auth_call["AuthParameters"]["USERNAME"] == "testuser"
            assert auth_call["AuthParameters"]["PASSWORD"] == "Pass123!"
            assert "SECRET_HASH" not in auth_call["AuthParameters"]

    def test_get_token_with_secret(self):
        """Test getting access token with client secret (SECRET_HASH)."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            mock_cognito.initiate_auth.return_value = {
                "AuthenticationResult": {"AccessToken": "test-access-token-with-secret"}
            }

            client_secret = "test-client-secret"
            token = get_cognito_access_token(
                pool_id="us-west-2_testpool",
                client_id="client123",
                username="testuser",
                password="Pass123!",
                region="us-west-2",
                client_secret=client_secret,
            )

            assert token == "test-access-token-with-secret"

            # Verify SECRET_HASH was calculated and included
            auth_call = mock_cognito.initiate_auth.call_args[1]
            assert "SECRET_HASH" in auth_call["AuthParameters"]

            # Verify SECRET_HASH calculation
            message = "testuser" + "client123"
            expected_hash = base64.b64encode(
                hmac.new(client_secret.encode("utf-8"), msg=message.encode("utf-8"), digestmod=hashlib.sha256).digest()
            ).decode()

            assert auth_call["AuthParameters"]["SECRET_HASH"] == expected_hash


class TestEnsureIdentityPermissions:
    """Test ensure_identity_permissions function."""

    def test_ensure_permissions_success(self):
        """Test successfully updating IAM role with Identity permissions."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_iam = Mock()
            mock_boto3.return_value = mock_iam

            role_arn = "arn:aws:iam::123456789012:role/AgentCoreRole"
            provider_arns = [
                "arn:aws:bedrock-agentcore:us-west-2:123456789012:credential-provider/default/oauth2/MyCognito",
                "arn:aws:bedrock-agentcore:us-west-2:123456789012:credential-provider/default/oauth2/MyGitHub",
            ]

            ensure_identity_permissions(
                role_arn=role_arn,
                provider_arns=provider_arns,
                region="us-west-2",
                account_id="123456789012",
            )

            # Verify trust policy was updated
            mock_iam.update_assume_role_policy.assert_called_once()
            trust_call = mock_iam.update_assume_role_policy.call_args[1]
            assert trust_call["RoleName"] == "AgentCoreRole"

            trust_policy = json.loads(trust_call["PolicyDocument"])
            assert trust_policy["Statement"][0]["Principal"]["Service"] == "bedrock-agentcore.amazonaws.com"

            # Verify inline policy was added
            mock_iam.put_role_policy.assert_called_once()
            policy_call = mock_iam.put_role_policy.call_args[1]
            assert policy_call["RoleName"] == "AgentCoreRole"
            assert policy_call["PolicyName"] == "AgentCoreIdentityAccess"

            policy_doc = json.loads(policy_call["PolicyDocument"])
            # Verify workload access statement
            workload_stmt = next(s for s in policy_doc["Statement"] if s["Sid"] == "WorkloadAccessTokenExchange")
            assert "bedrock-agentcore:GetWorkloadAccessToken" in workload_stmt["Action"]

            # Verify OAuth2 token access statement
            oauth_stmt = next(s for s in policy_doc["Statement"] if s["Sid"] == "ResourceOAuth2TokenAccess")
            assert "bedrock-agentcore:GetResourceOauth2Token" in oauth_stmt["Action"]
            assert provider_arns[0] in oauth_stmt["Resource"]
            assert provider_arns[1] in oauth_stmt["Resource"]

            # Verify secrets manager statement
            secrets_stmt = next(s for s in policy_doc["Statement"] if s["Sid"] == "CredentialProviderSecrets")
            assert "secretsmanager:GetSecretValue" in secrets_stmt["Action"]

    def test_ensure_permissions_with_logger(self):
        """Test ensure_permissions with custom logger."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_iam = Mock()
            mock_boto3.return_value = mock_iam

            mock_logger = Mock()
            role_arn = "arn:aws:iam::123456789012:role/AgentCoreRole"
            provider_arns = ["arn:aws:bedrock-agentcore:us-west-2:123456789012:credential-provider/default/oauth2/Test"]

            ensure_identity_permissions(
                role_arn=role_arn,
                provider_arns=provider_arns,
                region="us-west-2",
                account_id="123456789012",
                logger=mock_logger,
            )

            # Verify logger was used
            assert mock_logger.info.call_count >= 2

    def test_ensure_permissions_failure(self):
        """Test error handling when IAM update fails."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_iam = Mock()
            mock_iam.update_assume_role_policy.side_effect = ClientError(
                {"Error": {"Code": "NoSuchEntity", "Message": "Role not found"}}, "UpdateAssumeRolePolicy"
            )
            mock_boto3.return_value = mock_iam

            role_arn = "arn:aws:iam::123456789012:role/NonExistentRole"
            provider_arns = ["arn:aws:bedrock-agentcore:us-west-2:123456789012:credential-provider/default/oauth2/Test"]

            with pytest.raises(ClientError):
                ensure_identity_permissions(
                    role_arn=role_arn,
                    provider_arns=provider_arns,
                    region="us-west-2",
                    account_id="123456789012",
                )


class TestIdentityCognitoManager:
    """Test IdentityCognitoManager class."""

    def test_init(self):
        """Test manager initialization."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            manager = IdentityCognitoManager("us-west-2")

            assert manager.region == "us-west-2"
            assert manager.cognito_client is not None
            mock_boto3.assert_called_once_with("cognito-idp", region_name="us-west-2")

    def test_generate_random_id(self):
        """Test random ID generation."""
        id1 = IdentityCognitoManager.generate_random_id()
        id2 = IdentityCognitoManager.generate_random_id()

        assert len(id1) == 8
        assert len(id2) == 8
        assert id1 != id2  # Should be unique

    def test_create_dual_pool_setup_success(self):
        """Test successful dual pool creation."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            # Mock responses for runtime pool
            mock_cognito.create_user_pool.side_effect = [
                {"UserPool": {"Id": "us-west-2_runtime123"}},
                {"UserPool": {"Id": "us-west-2_identity456"}},
            ]
            mock_cognito.create_user_pool_domain.return_value = {}
            mock_cognito.describe_user_pool_domain.return_value = {"DomainDescription": {"Status": "ACTIVE"}}
            mock_cognito.create_user_pool_client.side_effect = [
                {"UserPoolClient": {"ClientId": "runtime_client_123"}},
                {"UserPoolClient": {"ClientId": "identity_client_456", "ClientSecret": "identity_secret_789"}},
            ]
            mock_cognito.admin_create_user.return_value = {}
            mock_cognito.admin_set_user_password.return_value = {}

            manager = IdentityCognitoManager("us-west-2")
            result = manager.create_dual_pool_setup()

            # Verify both pools were created
            assert "runtime" in result
            assert "identity" in result

            # Verify runtime pool config
            assert result["runtime"]["pool_id"] == "us-west-2_runtime123"
            assert result["runtime"]["client_id"] == "runtime_client_123"
            assert "discovery_url" in result["runtime"]
            assert "username" in result["runtime"]
            assert "password" in result["runtime"]

            # Verify identity pool config
            assert result["identity"]["pool_id"] == "us-west-2_identity456"
            assert result["identity"]["client_id"] == "identity_client_456"
            assert result["identity"]["client_secret"] == "identity_secret_789"
            assert "discovery_url" in result["identity"]
            assert "username" in result["identity"]
            assert "password" in result["identity"]

            # Verify correct number of boto3 calls
            assert mock_cognito.create_user_pool.call_count == 2
            assert mock_cognito.create_user_pool_domain.call_count == 2
            assert mock_cognito.create_user_pool_client.call_count == 2
            assert mock_cognito.admin_create_user.call_count == 2
            assert mock_cognito.admin_set_user_password.call_count == 2

    def test_create_dual_pool_setup_failure(self):
        """Test dual pool creation failure."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_cognito.create_user_pool.side_effect = ClientError(
                {"Error": {"Code": "LimitExceededException", "Message": "Pool limit exceeded"}}, "CreateUserPool"
            )
            mock_boto3.return_value = mock_cognito

            manager = IdentityCognitoManager("us-west-2")

            with pytest.raises(ClientError):
                manager.create_dual_pool_setup()

    def test_create_runtime_pool(self):
        """Test runtime pool creation."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            mock_cognito.create_user_pool.return_value = {"UserPool": {"Id": "us-west-2_runtime"}}
            mock_cognito.create_user_pool_domain.return_value = {}
            mock_cognito.describe_user_pool_domain.return_value = {"DomainDescription": {"Status": "ACTIVE"}}
            mock_cognito.create_user_pool_client.return_value = {"UserPoolClient": {"ClientId": "runtime_client"}}
            mock_cognito.admin_create_user.return_value = {}
            mock_cognito.admin_set_user_password.return_value = {}

            manager = IdentityCognitoManager("us-west-2")
            result = manager._create_runtime_pool()

            # Verify runtime pool has no client secret
            assert "client_secret" not in result or result.get("client_secret") is None
            assert result["client_id"] == "runtime_client"

            # Verify ExplicitAuthFlows includes USER_PASSWORD_AUTH
            client_call = mock_cognito.create_user_pool_client.call_args[1]
            assert "ALLOW_USER_PASSWORD_AUTH" in client_call["ExplicitAuthFlows"]
            assert client_call.get("GenerateSecret") is False or "GenerateSecret" not in client_call

    def test_create_identity_pool(self):
        """Test identity pool creation."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            mock_cognito.create_user_pool.return_value = {"UserPool": {"Id": "us-west-2_identity"}}
            mock_cognito.create_user_pool_domain.return_value = {}
            mock_cognito.describe_user_pool_domain.return_value = {"DomainDescription": {"Status": "ACTIVE"}}
            mock_cognito.create_user_pool_client.return_value = {
                "UserPoolClient": {"ClientId": "identity_client", "ClientSecret": "identity_secret"}
            }
            mock_cognito.admin_create_user.return_value = {}
            mock_cognito.admin_set_user_password.return_value = {}

            manager = IdentityCognitoManager("us-west-2")
            result = manager._create_identity_pool()

            # Verify identity pool has client secret
            assert result["client_secret"] == "identity_secret"
            assert result["client_id"] == "identity_client"

            # Verify OAuth configuration
            client_call = mock_cognito.create_user_pool_client.call_args[1]
            assert client_call["GenerateSecret"] is True
            assert "code" in client_call["AllowedOAuthFlows"]
            assert "openid" in client_call["AllowedOAuthScopes"]

    def test_wait_for_domain_success(self):
        """Test waiting for domain to become active."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            # Domain becomes active after 2 attempts
            mock_cognito.describe_user_pool_domain.side_effect = [
                {"DomainDescription": {"Status": "CREATING"}},
                {"DomainDescription": {"Status": "ACTIVE"}},
            ]

            manager = IdentityCognitoManager("us-west-2")

            with patch("time.sleep"):
                manager._wait_for_domain("test-domain")

            assert mock_cognito.describe_user_pool_domain.call_count == 2

    def test_wait_for_domain_timeout(self):
        """Test waiting for domain times out gracefully."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            # Domain never becomes active
            mock_cognito.describe_user_pool_domain.return_value = {"DomainDescription": {"Status": "CREATING"}}

            manager = IdentityCognitoManager("us-west-2")

            with patch("time.sleep"):
                # Should complete without raising exception
                manager._wait_for_domain("test-domain", max_attempts=3)

            assert mock_cognito.describe_user_pool_domain.call_count == 3

    def test_wait_for_domain_client_error(self):
        """Test waiting for domain handles client errors."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            # First call fails, second succeeds
            mock_cognito.describe_user_pool_domain.side_effect = [
                ClientError(
                    {"Error": {"Code": "ResourceNotFoundException", "Message": "Not found"}}, "DescribeUserPoolDomain"
                ),
                {"DomainDescription": {"Status": "ACTIVE"}},
            ]

            manager = IdentityCognitoManager("us-west-2")

            with patch("time.sleep"):
                manager._wait_for_domain("test-domain")

            assert mock_cognito.describe_user_pool_domain.call_count == 2

    def test_generate_password(self):
        """Test password generation."""
        # Generate multiple passwords to test characteristics more reliably
        passwords = [IdentityCognitoManager._generate_password() for _ in range(5)]

        # All should be correct length
        for password in passwords:
            assert len(password) == 16

        # Test across all generated passwords (more reliable than single password)
        all_chars = "".join(passwords)
        has_letter = any(c.isalpha() for c in all_chars)
        has_digit = any(c.isdigit() for c in all_chars)

        assert has_letter, "Generated passwords should contain letters"
        assert has_digit, "Generated passwords should contain digits"

        # Each individual password should have some complexity
        for password in passwords:
            # At least 2 different character types
            has_lower = any(c.islower() for c in password)
            has_upper = any(c.isupper() for c in password)
            has_num = any(c.isdigit() for c in password)
            has_special = any(not c.isalnum() for c in password)

            char_types = sum([has_lower, has_upper, has_num, has_special])
            assert char_types >= 2, f"Password should have at least 2 character types: {password}"

    def test_cleanup_cognito_pools_success(self):
        """Test successful cleanup of Cognito pools."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            mock_cognito.describe_user_pool.side_effect = [
                {"UserPool": {"Domain": "runtime-domain"}},
                {"UserPool": {"Domain": "identity-domain"}},
            ]
            mock_cognito.delete_user_pool_domain.return_value = {}
            mock_cognito.delete_user_pool.return_value = {}

            manager = IdentityCognitoManager("us-west-2")

            with patch("time.sleep"):
                manager.cleanup_cognito_pools(
                    runtime_pool_id="us-west-2_runtime123", identity_pool_id="us-west-2_identity456"
                )

            # Verify both pools were deleted
            assert mock_cognito.delete_user_pool_domain.call_count == 2
            assert mock_cognito.delete_user_pool.call_count == 2

    def test_cleanup_cognito_pools_no_domain(self):
        """Test cleanup when pools have no custom domain."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            mock_cognito.describe_user_pool.return_value = {"UserPool": {}}  # No Domain key
            mock_cognito.delete_user_pool.return_value = {}

            manager = IdentityCognitoManager("us-west-2")

            with patch("time.sleep"):
                manager.cleanup_cognito_pools(runtime_pool_id="us-west-2_runtime123")

            # Verify domain deletion was not attempted
            mock_cognito.delete_user_pool_domain.assert_not_called()
            # But pool was still deleted
            mock_cognito.delete_user_pool.assert_called_once()

    def test_cleanup_cognito_pools_already_deleted(self):
        """Test cleanup when pools are already deleted."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            mock_cognito.describe_user_pool.side_effect = ClientError(
                {"Error": {"Code": "ResourceNotFoundException", "Message": "Pool not found"}}, "DescribeUserPool"
            )

            manager = IdentityCognitoManager("us-west-2")

            # Should not raise exception
            manager.cleanup_cognito_pools(runtime_pool_id="us-west-2_runtime123")

    def test_cleanup_cognito_pools_partial_failure(self):
        """Test cleanup continues when one pool deletion fails."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            # First pool succeeds, second fails
            mock_cognito.describe_user_pool.side_effect = [
                {"UserPool": {"Domain": "runtime-domain"}},
                ClientError({"Error": {"Code": "InternalError", "Message": "Internal error"}}, "DescribeUserPool"),
            ]
            mock_cognito.delete_user_pool_domain.return_value = {}
            mock_cognito.delete_user_pool.return_value = {}

            manager = IdentityCognitoManager("us-west-2")

            with patch("time.sleep"):
                # Should not raise exception
                manager.cleanup_cognito_pools(
                    runtime_pool_id="us-west-2_runtime123", identity_pool_id="us-west-2_identity456"
                )

            # First pool was deleted
            assert mock_cognito.delete_user_pool.call_count == 1

    def test_delete_user_pool_success(self):
        """Test successful deletion of a single user pool."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            mock_cognito.describe_user_pool.return_value = {"UserPool": {"Domain": "test-domain"}}
            mock_cognito.delete_user_pool_domain.return_value = {}
            mock_cognito.delete_user_pool.return_value = {}

            manager = IdentityCognitoManager("us-west-2")

            with patch("time.sleep"):
                manager._delete_user_pool("us-west-2_test123", "Test")

            mock_cognito.delete_user_pool_domain.assert_called_once()
            mock_cognito.delete_user_pool.assert_called_once_with(UserPoolId="us-west-2_test123")

    def test_delete_user_pool_domain_deletion_error(self):
        """Test pool deletion continues when domain deletion fails."""
        with patch("bedrock_agentcore_starter_toolkit.operations.identity.helpers.boto3.client") as mock_boto3:
            mock_cognito = Mock()
            mock_boto3.return_value = mock_cognito

            mock_cognito.describe_user_pool.return_value = {"UserPool": {"Domain": "test-domain"}}
            mock_cognito.delete_user_pool_domain.side_effect = ClientError(
                {"Error": {"Code": "InvalidParameterException", "Message": "Domain error"}}, "DeleteUserPoolDomain"
            )
            mock_cognito.delete_user_pool.return_value = {}

            manager = IdentityCognitoManager("us-west-2")

            with patch("time.sleep"):
                # Should not raise exception
                manager._delete_user_pool("us-west-2_test123", "Test")

            # Pool deletion was still attempted
            mock_cognito.delete_user_pool.assert_called_once()


class TestHelperUtilities:
    """Test utility functions."""

    def test_random_suffix_default_length(self):
        """Test _random_suffix generates correct length."""
        suffix = _random_suffix()
        assert len(suffix) == 4
        assert suffix.isalnum()

    def test_random_suffix_custom_length(self):
        """Test _random_suffix with custom length."""
        suffix = _random_suffix(length=8)
        assert len(suffix) == 8
        assert suffix.isalnum()

    def test_random_suffix_uniqueness(self):
        """Test that multiple calls generate different suffixes."""
        suffixes = [_random_suffix() for _ in range(10)]
        # Should have high probability of being unique
        assert len(set(suffixes)) > 5

    def test_generate_password_default_length(self):
        """Test _generate_password generates correct length."""
        password = _generate_password()
        assert len(password) == 16

    def test_generate_password_custom_length(self):
        """Test _generate_password with custom length."""
        password = _generate_password(length=24)
        assert len(password) == 24

    def test_generate_password_complexity(self):
        """Test password contains various character types."""
        password = _generate_password(length=50)
        # Should contain at least one letter, digit, and special char
        has_letter = any(c.isalpha() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        assert has_letter
        assert has_digit
        assert has_special

    def test_generate_password_uniqueness(self):
        """Test that passwords are unique."""
        passwords = [_generate_password() for _ in range(10)]
        assert len(set(passwords)) == 10  # All should be unique
