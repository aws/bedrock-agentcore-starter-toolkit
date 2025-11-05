"""Helper functions for Identity service operations."""

import json
import random
import string
import time
import uuid
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError


def create_cognito_oauth_pool(
    base_name: str = "AgentCoreTest",
    region: str = "us-west-2",
    create_test_user: bool = True,
    agentcore_callback_url: Optional[str] = None,
    use_for_runtime_auth: bool = False,
) -> Dict:
    """Create a Cognito user pool configured for OAuth 2.0 flows.

    Args:
        base_name: Base name for the pool
        region: AWS region
        create_test_user: Whether to create a test user
        agentcore_callback_url: AgentCore callback URL to register
        use_for_runtime_auth: Convenience flag - if True, creates client without secret.
                             Users can create pools however they want; this is just a helper.

    Returns:
        Dict with pool_id, client_id, client_secret (if generated), discovery_url, etc.
    """
    cognito = boto3.client("cognito-idp", region_name=region)

    # Generate unique names
    pool_name = f"{base_name}Pool{_random_suffix()}"
    domain_name = f"{base_name.lower()}-{_random_suffix(5)}"

    # Create user pool
    pool_response = cognito.create_user_pool(PoolName=pool_name)
    pool_id = pool_response["UserPool"]["Id"]

    # Create domain
    cognito.create_user_pool_domain(Domain=domain_name, UserPoolId=pool_id)

    # Build callback URLs
    callback_urls = [f"https://bedrock-agentcore.{region}.amazonaws.com/identities/oauth2/callback"]
    if agentcore_callback_url:
        callback_urls.append(agentcore_callback_url)

    # Build client configuration
    client_config = {
        "UserPoolId": pool_id,
        "ClientName": f"{base_name}Client",
        "CallbackURLs": callback_urls,
        "AllowedOAuthFlows": ["code"],
        "AllowedOAuthScopes": ["openid", "profile", "email"],
        "AllowedOAuthFlowsUserPoolClient": True,
        "SupportedIdentityProviders": ["COGNITO"],
    }

    # Configure auth flows based on purpose
    if use_for_runtime_auth:
        # Runtime auth: No secret needed for USER_PASSWORD_AUTH
        client_config["ExplicitAuthFlows"] = ["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"]
    else:
        # Identity/3LO: Secret required for authorization code flow
        client_config["GenerateSecret"] = True
        client_config["ExplicitAuthFlows"] = ["ALLOW_REFRESH_TOKEN_AUTH"]

    client_response = cognito.create_user_pool_client(**client_config)

    client_id = client_response["UserPoolClient"]["ClientId"]
    client_secret = client_response["UserPoolClient"].get("ClientSecret")

    # Build URLs
    discovery_url = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/openid-configuration"
    hosted_ui_url = f"https://{domain_name}.auth.{region}.amazoncognito.com"

    result = {
        "pool_id": pool_id,
        "pool_name": pool_name,
        "client_id": client_id,
        "discovery_url": discovery_url,
        "hosted_ui_url": hosted_ui_url,
        "domain": domain_name,
        "region": region,
    }

    # Only include client_secret if it was generated
    if client_secret:
        result["client_secret"] = client_secret

    # Create test user if requested
    if create_test_user:
        username = f"testuser{random.randint(1000, 9999)}"
        password = _generate_password()

        cognito.admin_create_user(UserPoolId=pool_id, Username=username, MessageAction="SUPPRESS")

        cognito.admin_set_user_password(UserPoolId=pool_id, Username=username, Password=password, Permanent=True)

        result["username"] = username
        result["password"] = password

    return result


def update_cognito_callback_urls(pool_id: str, client_id: str, callback_url: str, region: str = "us-west-2"):
    """Update Cognito app client to include AgentCore callback URL.

    Args:
        pool_id: Cognito user pool ID
        client_id: App client ID
        callback_url: AgentCore callback URL to add
        region: AWS region
    """
    cognito = boto3.client("cognito-idp", region_name=region)

    # Get current client settings
    client_response = cognito.describe_user_pool_client(UserPoolId=pool_id, ClientId=client_id)
    client_config = client_response["UserPoolClient"]

    # Get current callback URLs
    current_callbacks = client_config.get("CallbackURLs", [])

    # Add new callback URL if not already present
    if callback_url not in current_callbacks:
        current_callbacks.append(callback_url)

        # Update client
        cognito.update_user_pool_client(
            UserPoolId=pool_id,
            ClientId=client_id,
            CallbackURLs=current_callbacks,
            AllowedOAuthFlows=client_config.get("AllowedOAuthFlows", ["code"]),
            AllowedOAuthScopes=client_config.get("AllowedOAuthScopes", ["openid"]),
            AllowedOAuthFlowsUserPoolClient=True,
            SupportedIdentityProviders=client_config.get("SupportedIdentityProviders", ["COGNITO"]),
        )


def get_cognito_access_token(
    pool_id: str,
    client_id: str,
    username: str,
    password: str,
    region: str = "us-west-2",
    client_secret: Optional[str] = None,
) -> str:
    """Retrieve an access token from Cognito using username/password.

    Args:
        pool_id: Cognito user pool ID
        client_id: App client ID
        username: User's username
        password: User's password
        region: AWS region
        client_secret: App client secret (optional, provide if client has secret enabled)

    Returns:
        Access token string
    """
    import base64
    import hashlib
    import hmac

    cognito = boto3.client("cognito-idp", region_name=region)

    auth_parameters = {
        "USERNAME": username,
        "PASSWORD": password,
    }

    # Calculate SECRET_HASH if client secret provided
    if client_secret:
        message = username + client_id
        dig = hmac.new(client_secret.encode("utf-8"), msg=message.encode("utf-8"), digestmod=hashlib.sha256).digest()
        secret_hash = base64.b64encode(dig).decode()
        auth_parameters["SECRET_HASH"] = secret_hash

    response = cognito.initiate_auth(ClientId=client_id, AuthFlow="USER_PASSWORD_AUTH", AuthParameters=auth_parameters)

    return response["AuthenticationResult"]["AccessToken"]


def _random_suffix(length: int = 4) -> str:
    """Generate random alphanumeric suffix."""
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def _generate_password(length: int = 16) -> str:
    """Generate a secure random password."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
    return "".join(random.choices(chars, k=length))


def ensure_identity_permissions(role_arn: str, provider_arns: list, region: str, account_id: str, logger=None) -> None:
    """Ensure execution role has all necessary Identity permissions.

    Automatically updates IAM role with:
    1. Correct trust policy for bedrock-agentcore.amazonaws.com
    2. GetResourceOauth2Token permissions
    3. GetWorkloadAccessToken permissions
    4. Secrets Manager access for credential providers

    Args:
        role_arn: Execution role ARN to update
        provider_arns: List of credential provider ARNs
        region: AWS region
        account_id: AWS account ID
        logger: Optional logger instance
    """
    import logging

    import boto3

    if logger is None:
        logger = logging.getLogger(__name__)

    iam = boto3.client("iam", region_name=region)
    role_name = role_arn.split("/")[-1]

    try:
        # 1. Update trust policy
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                    "Condition": {
                        "StringEquals": {"aws:SourceAccount": account_id},
                        "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"},
                    },
                }
            ],
        }

        iam.update_assume_role_policy(RoleName=role_name, PolicyDocument=json.dumps(trust_policy))
        logger.info("✓ Updated trust policy for role: %s", role_name)

        # 2. Build resource list for providers
        secret_resources = []
        for provider_arn in provider_arns:
            provider_name = provider_arn.split("/")[-1]
            secret_resources.append(
                f"arn:aws:secretsmanager:{region}:{account_id}:secret:bedrock-agentcore-identity!default/oauth2/{provider_name}*"
            )

        # 3. Create comprehensive Identity permissions policy
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "WorkloadAccessTokenExchange",
                    "Effect": "Allow",
                    "Action": [
                        "bedrock-agentcore:GetWorkloadAccessToken",
                        "bedrock-agentcore:GetWorkloadAccessTokenForJWT",
                        "bedrock-agentcore:GetWorkloadAccessTokenForUserId",
                    ],
                    "Resource": [
                        f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default",
                        f"arn:aws:bedrock-agentcore:{region}:{account_id}:workload-identity-directory/default/workload-identity/*",
                    ],
                },
                {
                    "Sid": "ResourceOAuth2TokenAccess",
                    "Effect": "Allow",
                    "Action": [
                        "bedrock-agentcore:GetResourceOauth2Token",
                        "bedrock-agentcore:GetResourceApiKey",
                    ],
                    "Resource": [
                        f"arn:aws:bedrock-agentcore:{region}:{account_id}:token-vault/default",
                    ]
                    + provider_arns,
                },
                {
                    "Sid": "CredentialProviderSecrets",
                    "Effect": "Allow",
                    "Action": ["secretsmanager:GetSecretValue"],
                    "Resource": secret_resources,
                },
            ],
        }

        # 4. Put inline policy
        policy_name = "AgentCoreIdentityAccess"
        iam.put_role_policy(RoleName=role_name, PolicyName=policy_name, PolicyDocument=json.dumps(policy_document))

        logger.info("✓ Added Identity permissions to role: %s", role_name)

    except Exception as e:
        logger.error("Failed to update IAM permissions: %s", str(e))
        raise


class IdentityCognitoManager:
    """Manages Cognito User Pool setup for AgentCore Identity."""

    def __init__(self, region_name: str):
        """Initialize the Cognito manager.

        Args:
            region_name: AWS region name
        """
        import logging

        self.region = region_name
        self.cognito_client = boto3.client("cognito-idp", region_name=region_name)
        self.logger = logging.getLogger("bedrock_agentcore.identity.cognito")

    @staticmethod
    def generate_random_id() -> str:
        """Generate a random ID for Cognito resources."""
        return str(uuid.uuid4())[:8]

    def create_dual_pool_setup(self) -> Dict[str, Any]:
        """Create complete Cognito setup for Identity.

        Creates two user pools:
        1. Runtime Pool: For agent inbound authentication (JWT bearer tokens)
        2. Identity Pool: For agent outbound authentication (external services)

        Returns:
            Dictionary with both pool configurations and test credentials
        """
        self.logger.info("Creating Cognito pools for Identity...")

        try:
            # Create Runtime User Pool (for inbound auth to agent)
            runtime_config = self._create_runtime_pool()
            self.logger.info("✓ Created Runtime User Pool: %s", runtime_config["pool_id"])

            # Create Identity User Pool (for outbound auth to external services)
            identity_config = self._create_identity_pool()
            self.logger.info("✓ Created Identity User Pool: %s", identity_config["pool_id"])

            result = {
                "runtime": runtime_config,
                "identity": identity_config,
            }

            self.logger.info("✅ Cognito setup complete!")
            return result

        except Exception as e:
            self.logger.error("Failed to create Cognito pools: %s", str(e))
            raise

    def _create_runtime_pool(self) -> Dict[str, Any]:
        """Create Runtime User Pool for agent inbound authentication.

        Returns:
            Runtime pool configuration
        """
        pool_name = f"AgentCoreRuntimePool-{self.generate_random_id()}"

        # Create User Pool
        user_pool_response = self.cognito_client.create_user_pool(
            PoolName=pool_name,
            AdminCreateUserConfig={"AllowAdminCreateUserOnly": True},
        )
        pool_id = user_pool_response["UserPool"]["Id"]

        # Create Domain
        domain_prefix = f"agentcore-runtime-{self.generate_random_id()}"
        self.cognito_client.create_user_pool_domain(Domain=domain_prefix, UserPoolId=pool_id)

        # Wait for domain to be active
        self._wait_for_domain(domain_prefix)

        # Create Client (need secret for get-token command)
        client_response = self.cognito_client.create_user_pool_client(
            UserPoolId=pool_id,
            ClientName=f"RuntimeClient-{self.generate_random_id()}",
            GenerateSecret=False,
            ExplicitAuthFlows=["ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"],
        )

        client_id = client_response["UserPoolClient"]["ClientId"]

        # Create test user
        username = f"testuser{self.generate_random_id()}"
        password = self._generate_password()

        self.cognito_client.admin_create_user(UserPoolId=pool_id, Username=username)
        self.cognito_client.admin_set_user_password(
            UserPoolId=pool_id, Username=username, Password=password, Permanent=True
        )

        discovery_url = f"https://cognito-idp.{self.region}.amazonaws.com/{pool_id}/.well-known/openid-configuration"

        return {
            "pool_id": pool_id,
            "client_id": client_id,
            "discovery_url": discovery_url,
            "domain_prefix": domain_prefix,
            "username": username,
            "password": password,
        }

    def _create_identity_pool(self) -> Dict[str, Any]:
        """Create Identity User Pool for external service authentication.

        Returns:
            Identity pool configuration
        """
        pool_name = f"AgentCoreIdentityPool-{self.generate_random_id()}"

        # Create User Pool
        user_pool_response = self.cognito_client.create_user_pool(
            PoolName=pool_name,
            AdminCreateUserConfig={"AllowAdminCreateUserOnly": True},
        )
        pool_id = user_pool_response["UserPool"]["Id"]

        # Create Domain
        domain_prefix = f"agentcore-identity-{self.generate_random_id()}"
        self.cognito_client.create_user_pool_domain(Domain=domain_prefix, UserPoolId=pool_id)

        # Wait for domain to be active
        self._wait_for_domain(domain_prefix)

        # Create Client with secret (for credential provider)
        client_response = self.cognito_client.create_user_pool_client(
            UserPoolId=pool_id,
            ClientName=f"IdentityClient-{self.generate_random_id()}",
            GenerateSecret=True,
            CallbackURLs=[f"https://bedrock-agentcore.{self.region}.amazonaws.com/identities/oauth2/callback"],
            AllowedOAuthFlows=["code"],
            AllowedOAuthScopes=["openid", "profile", "email"],
            AllowedOAuthFlowsUserPoolClient=True,
            SupportedIdentityProviders=["COGNITO"],
        )

        client_id = client_response["UserPoolClient"]["ClientId"]
        client_secret = client_response["UserPoolClient"]["ClientSecret"]

        # Create test user
        username = f"externaluser{self.generate_random_id()}"
        password = self._generate_password()

        self.cognito_client.admin_create_user(UserPoolId=pool_id, Username=username)
        self.cognito_client.admin_set_user_password(
            UserPoolId=pool_id, Username=username, Password=password, Permanent=True
        )

        discovery_url = f"https://cognito-idp.{self.region}.amazonaws.com/{pool_id}/.well-known/openid-configuration"

        return {
            "pool_id": pool_id,
            "client_id": client_id,
            "client_secret": client_secret,
            "discovery_url": discovery_url,
            "domain_prefix": domain_prefix,
            "username": username,
            "password": password,
        }

    def _wait_for_domain(self, domain_prefix: str, max_attempts: int = 30) -> None:
        """Wait for Cognito domain to be active.

        Args:
            domain_prefix: Domain prefix to check
            max_attempts: Maximum number of attempts
        """
        for _ in range(max_attempts):
            try:
                response = self.cognito_client.describe_user_pool_domain(Domain=domain_prefix)
                if response.get("DomainDescription", {}).get("Status") == "ACTIVE":
                    return
            except ClientError:
                pass
            time.sleep(1)

        self.logger.warning("Domain may not be fully available yet")

    @staticmethod
    def _generate_password() -> str:
        """Generate a secure random password.

        Returns:
            Random password string
        """
        import random
        import string

        # Generate 16-char password with mixed case, numbers, and symbols
        chars = string.ascii_letters + string.digits + "!@#$%^&*()_+-="
        return "".join(random.choice(chars) for _ in range(16))

    def cleanup_cognito_pools(self, runtime_pool_id: str = None, identity_pool_id: str = None) -> None:
        """Delete Cognito user pools and associated resources.

        Args:
            runtime_pool_id: Runtime user pool ID to delete
            identity_pool_id: Identity user pool ID to delete
        """
        self.logger.info("🧹 Cleaning up Cognito resources...")

        # Delete Runtime Pool
        if runtime_pool_id:
            self._delete_user_pool(runtime_pool_id, "Runtime")

        # Delete Identity Pool
        if identity_pool_id:
            self._delete_user_pool(identity_pool_id, "Identity")

        self.logger.info("✅ Cognito cleanup complete")

    def _delete_user_pool(self, pool_id: str, pool_type: str) -> None:
        """Delete a user pool and its domain.

        Args:
            pool_id: User pool ID to delete
            pool_type: Type description for logging (Runtime/Identity)
        """
        try:
            # Get pool details to find domain
            pool_desc = self.cognito_client.describe_user_pool(UserPoolId=pool_id)

            # Try to get domain
            domain = pool_desc["UserPool"].get("Domain")
            if domain:
                self.logger.info("  • Deleting %s pool domain: %s", pool_type, domain)
                try:
                    self.cognito_client.delete_user_pool_domain(UserPoolId=pool_id, Domain=domain)
                    self.logger.info("    ✓ Domain deleted")
                    time.sleep(5)  # Wait for domain deletion
                except Exception as e:
                    self.logger.warning("    ⚠️  Error deleting domain: %s", str(e))

            # Delete the pool
            self.logger.info("  • Deleting %s user pool: %s", pool_type, pool_id)
            self.cognito_client.delete_user_pool(UserPoolId=pool_id)
            self.logger.info("    ✓ User pool deleted")

        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceNotFoundException":
                self.logger.info("    ✓ %s pool already deleted", pool_type)
            else:
                self.logger.warning("    ⚠️  Error deleting %s pool: %s", pool_type, str(e))
