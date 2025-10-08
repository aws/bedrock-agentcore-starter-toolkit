"""Client for interacting with Bedrock AgentCore Gateway services."""

import json
import logging
import time
import urllib.parse
import uuid
from typing import Any, Dict, Optional

import boto3
import urllib3

from .constants import (
    API_MODEL_BUCKETS,
    CREATE_OPENAPI_TARGET_INVALID_CREDENTIALS_SHAPE_EXCEPTION_MESSAGE,
    LAMBDA_CONFIG,
)
from .create_lambda import create_test_lambda
from .create_role import create_gateway_execution_role
from .exceptions import GatewaySetupException


class GatewayClient:
    """High-level client for Bedrock AgentCore Gateway operations."""

    def __init__(self, region_name: Optional[str] = None, endpoint_url: Optional[str] = None):
        """Initialize the Gateway client.

        Args:
            region_name: AWS region name (defaults to us-west-2)
            endpoint_url: Custom endpoint URL for the Gateway service
        """
        self.region = region_name or "us-west-2"

        if endpoint_url:
            self.client = boto3.client(
                "bedrock-agentcore-control",
                region_name=self.region,
                endpoint_url=endpoint_url,
            )
        else:
            self.client = boto3.client("bedrock-agentcore-control", region_name=self.region)

        self.session = boto3.Session(region_name=self.region)

        # Initialize the logger
        self.logger = logging.getLogger("bedrock_agentcore.gateway")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def create_mcp_gateway(
        self,
        name=None,
        role_arn=None,
        authorizer_config=None,
        enable_semantic_search=True,
    ) -> dict:
        """Creates an MCP Gateway.

        :param name: optional - the name of the gateway (defaults to TestGateway).
        :param role_arn: optional - the role arn to use (creates one if none provided).
        :param authorizer_config: optional - the authorizer config (will create one if none provided).
        :param enable_semantic_search: optional - whether to enable search tool (defaults to True).
        :return: the created Gateway
        """
        if not name:
            name = f"TestGateway{GatewayClient.generate_random_id()}"
        if not role_arn:
            self.logger.info("Role not provided, creating an execution role to use")
            role_arn = create_gateway_execution_role(self.session, self.logger)
            self.logger.info("✓ Successfully created execution role for Gateway")
        if not authorizer_config:
            self.logger.info("Authorizer config not provided, creating an authorizer to use")
            cognito_result = self.create_oauth_authorizer_with_cognito(name)
            self.logger.info("✓ Successfully created authorizer for Gateway")
            authorizer_config = cognito_result["authorizer_config"]
        create_request = {
            "name": name,
            "roleArn": role_arn,
            "protocolType": "MCP",
            "authorizerType": "CUSTOM_JWT",
            "authorizerConfiguration": authorizer_config,
            "exceptionLevel": "DEBUG",
        }
        if enable_semantic_search:
            create_request["protocolConfiguration"] = {"mcp": {"searchType": "SEMANTIC"}}
        self.logger.info("Creating Gateway")
        self.logger.debug("Creating gateway with params: %s", json.dumps(create_request, indent=2))
        gateway = self.client.create_gateway(**create_request)
        self.logger.info("✓ Created Gateway: %s", gateway["gatewayArn"])
        self.logger.info("  Gateway URL: %s", gateway["gatewayUrl"])

        # Wait for gateway to be ready
        self.logger.info("  Waiting for Gateway to be ready...")
        self.__wait_for_ready(
            method=self.client.get_gateway,
            identifiers={"gatewayIdentifier": gateway["gatewayId"]},
            resource_name="Gateway",
        )
        self.logger.info("\n✅Gateway is ready")
        return gateway

    def create_mcp_gateway_target(
        self,
        gateway: dict,
        name=None,
        target_type="lambda",
        target_payload=None,
        credentials=None,
    ) -> dict:
        """Creates an MCP Gateway Target.

        :param gateway: the gateway (output of create_mcp_gateway or calling get_gateway() with boto3 client).
        :param name: optional - the name of the target (defaults to TestGatewayTarget).
        :param target_type: optional - the type of the target e.g. one of "lambda" |
                            "openApiSchema" | "smithyModel" (defaults to "lambda").
        :param target_payload: only required for openApiSchema target - the specification of that target.
        :param credentials: only use with openApiSchema target - the credentials for calling this target
                            (api key or oauth2).
        :return: the created target.
        """
        # there is no name, create one
        if not name:
            name = f"TestGatewayTarget{GatewayClient.generate_random_id()}"
        # instantiate base creation request
        create_request = {
            "gatewayIdentifier": gateway["gatewayId"],
            "name": name,
            "targetConfiguration": {"mcp": {target_type: target_payload}},
            "credentialProviderConfigurations": [{"credentialProviderType": "GATEWAY_IAM_ROLE"}],
        }
        # handle cases of missing target payloads across smithy and lambda (default to something)
        if not target_payload and target_type == "lambda":
            create_request |= self.__handle_lambda_target_creation(gateway["roleArn"])
        if not target_payload and target_type == "smithyModel":
            region_bucket = API_MODEL_BUCKETS.get(self.region)
            if not region_bucket:
                raise Exception(
                    "Automatic smithyModel creation is not supported in this region. "
                    "Please try again by explicitly providing a smithyModel via targetPayload."
                )
            create_request |= {
                "targetConfiguration": {
                    "mcp": {"smithyModel": {"s3": {"uri": f"s3://{region_bucket}/dynamodb-smithy.json"}}}
                },
                "credentialProviderConfigurations": [{"credentialProviderType": "GATEWAY_IAM_ROLE"}],
            }
        # open api schemas need a target config with them
        if not target_payload and target_type == "openApiSchema":
            raise Exception("You must provide a target configuration for your OpenAPI specification.")
        # handle open api schema
        if target_type == "openApiSchema":
            create_request |= self.__handle_openapi_target_credential_provider_creation(
                name=name, credentials=credentials
            )
        # create the target
        self.logger.info("Creating Target")
        self.logger.info(create_request)
        self.logger.debug("Creating target with params: %s", json.dumps(create_request, indent=2))
        target = self.client.create_gateway_target(**create_request)
        self.logger.info("✓ Added target successfully (ID: %s)", target["targetId"])
        self.logger.info("  Waiting for target to be ready...")
        # poll till target is in READY state
        self.__wait_for_ready(
            method=self.client.get_gateway_target,
            identifiers={
                "gatewayIdentifier": gateway["gatewayId"],
                "targetId": target["targetId"],
            },
            resource_name="Target",
        )
        self.logger.info("\n✅Target is ready")
        return target

    def fix_iam_permissions(self, gateway: dict) -> None:
        """Fix IAM role trust policy for the gateway.

        :param gateway: the gateway dict containing roleArn
        """
        # Check for None gateway
        if gateway is None:
            return

        # Check for missing roleArn
        role_arn = gateway.get("roleArn")
        if not role_arn:
            return

        sts = boto3.client("sts")
        iam = boto3.client("iam")

        account_id = sts.get_caller_identity()["Account"]
        role_name = role_arn.split("/")[-1]

        # Update trust policy
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                    "Condition": {
                        "StringEquals": {"aws:SourceAccount": account_id},
                        "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{self.region}:{account_id}:*"},
                    },
                }
            ],
        }

        try:
            iam.update_assume_role_policy(RoleName=role_name, PolicyDocument=json.dumps(trust_policy))

            # Add Lambda permissions
            iam.put_role_policy(
                RoleName=role_name,
                PolicyName="LambdaInvokePolicy",
                PolicyDocument=json.dumps(
                    {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": ["lambda:InvokeFunction"],
                                "Resource": (
                                    f"arn:aws:lambda:{self.region}:{account_id}:function:AgentCoreLambdaTestFunction"
                                ),
                            }
                        ],
                    }
                ),
            )
            self.logger.info("✓ Fixed IAM permissions for Gateway")
        except Exception as e:
            self.logger.warning("⚠️ IAM role update failed: %s. Continuing with best effort.", str(e))

    def cleanup_gateway(self, gateway_id: str, client_info: Optional[Dict] = None) -> None:
        """Remove all resources associated with a gateway.

        :param gateway_id: the ID of the gateway to clean up
        :param client_info: optional Cognito client info for cleanup
        """
        self.logger.info("🧹 Cleaning up Gateway resources...")

        gateway_client = self.client

        # Step 1: List and delete all targets
        self.logger.info("  • Finding targets for gateway: %s", gateway_id)

        try:
            response = gateway_client.list_gateway_targets(gatewayIdentifier=gateway_id)
            # API returns targets in 'items' field
            targets = response.get("items", [])
            self.logger.info("    Found %s targets to delete", len(targets))

            for target in targets:
                target_id = target["targetId"]
                self.logger.info("  • Deleting target: %s", target_id)
                try:
                    gateway_client.delete_gateway_target(gatewayIdentifier=gateway_id, targetId=target_id)
                    self.logger.info("    ✓ Target deletion initiated: %s", target_id)
                    # Wait for deletion to complete
                    time.sleep(5)
                except Exception as e:
                    self.logger.warning("    ⚠️ Error deleting target %s: %s", target_id, str(e))

            # Verify all targets are deleted
            self.logger.info("  • Verifying targets deletion...")
            time.sleep(5)  # Additional wait
            verify_response = gateway_client.list_gateway_targets(gatewayIdentifier=gateway_id)
            remaining_targets = verify_response.get("items", [])
            if remaining_targets:
                self.logger.warning("    ⚠️ %s targets still remain", len(remaining_targets))
            else:
                self.logger.info("    ✓ All targets deleted")

        except Exception as e:
            self.logger.warning("    ⚠️ Error managing targets: %s", str(e))

        # Step 2: Delete the gateway
        try:
            self.logger.info("  • Deleting gateway: %s", gateway_id)
            gateway_client.delete_gateway(gatewayIdentifier=gateway_id)
            self.logger.info("    ✓ Gateway deleted: %s", gateway_id)
        except Exception as e:
            self.logger.warning("    ⚠️ Error deleting gateway: %s", str(e))

        # Step 3: Delete Cognito resources if provided
        if client_info and "user_pool_id" in client_info:
            cognito = boto3.client("cognito-idp", region_name=self.region)
            user_pool_id = client_info["user_pool_id"]

            # Delete domain first
            if "domain_prefix" in client_info:
                domain_prefix = client_info["domain_prefix"]
                self.logger.info("  • Deleting Cognito domain: %s", domain_prefix)
                try:
                    cognito.delete_user_pool_domain(UserPoolId=user_pool_id, Domain=domain_prefix)
                    self.logger.info("    ✓ Cognito domain deleted")
                    time.sleep(5)  # Wait for domain deletion
                except Exception as e:
                    self.logger.warning("    ⚠️ Error deleting Cognito domain: %s", str(e))

            # Now delete the user pool
            self.logger.info("  • Deleting Cognito user pool: %s", user_pool_id)
            try:
                cognito.delete_user_pool(UserPoolId=user_pool_id)
                self.logger.info("    ✓ Cognito user pool deleted")
            except Exception as e:
                self.logger.warning("    ⚠️ Error deleting Cognito user pool: %s", str(e))

        self.logger.info("✅ Cleanup complete")

    def __handle_lambda_target_creation(self, role_arn: str) -> Dict[str, Any]:
        """Create a test lambda.

        :return: the targetConfiguration for the Lambda.
        """
        lambda_arn = create_test_lambda(self.session, logger=self.logger, gateway_role_arn=role_arn)

        return {
            "targetConfiguration": {"mcp": {"lambda": {"lambdaArn": lambda_arn, "toolSchema": LAMBDA_CONFIG}}},
        }

    def __handle_openapi_target_credential_provider_creation(
        self, name: str, credentials: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate the credential provider config for open api target.

        :param name: the name of the target.
        :param credentials: credentials to use in setting up this target.
        :return: the credential provider config.
        """
        acps = self.session.client(service_name="bedrock-agentcore-control")
        if "api_key" in credentials:
            self.logger.info("Creating credential provider")
            credential_provider = acps.create_api_key_credential_provider(
                name=f"{name}-ApiKey-{self.generate_random_id()}",
                apiKey=credentials["api_key"],
            )
            self.logger.info(
                "✓ Added credential provider successfully (ARN: %s)",
                credential_provider["credentialProviderArn"],
            )
            target_cred_provider_config = {
                "credentialProviderType": "API_KEY",
                "credentialProvider": {
                    "apiKeyCredentialProvider": {
                        "providerArn": credential_provider["credentialProviderArn"],
                        "credentialLocation": credentials["credential_location"],
                        "credentialParameterName": credentials["credential_parameter_name"],
                    }
                },
            }
        elif "oauth2_provider_config" in credentials:
            self.logger.info("Creating credential provider")
            credential_provider = acps.create_oauth2_credential_provider(
                name=f"{name}-OAuth-Credentials-{self.generate_random_id()}",
                credentialProviderVendor="CustomOauth2",
                oauth2ProviderConfigInput=credentials["oauth2_provider_config"],
            )
            self.logger.info(
                "✓ Added credential provider successfully (ARN: %s)",
                credential_provider["credentialProviderArn"],
            )
            target_cred_provider_config = {
                "credentialProviderType": "OAUTH",
                "credentialProvider": {
                    "oauthCredentialProvider": {
                        "providerArn": credential_provider["credentialProviderArn"],
                        "scopes": credentials.get("scopes", []),
                    }
                },
            }
        else:
            raise Exception(CREATE_OPENAPI_TARGET_INVALID_CREDENTIALS_SHAPE_EXCEPTION_MESSAGE)
        return {"credentialProviderConfigurations": [target_cred_provider_config]}

    @staticmethod
    def __wait_for_ready(resource_name, method, identifiers, max_attempts: int = 30, delay: int = 2) -> None:
        """Wait for the resource to be ready.

        :param resource_name: the name of the resource.
        :param method: the method to be invoked.
        :param identifiers: the identifiers to fetch the resource (e.g. gateway id, target id).
        :param max_attempts: the maximum number of times to poll.
        :param delay: time delay in between polls.
        :return:
        """
        attempts = 0
        while True:
            response = method(**identifiers)
            status = response.get("status", "UNKNOWN")
            if not status == "CREATING":
                break
            time.sleep(delay)
            attempts += 1
            if attempts >= max_attempts:
                raise TimeoutError(f"{resource_name} not ready after {max_attempts} attempts")
        if status == "READY":
            return
        else:
            raise Exception(f"{resource_name} failed: {response}")

    # Generate unique IDs
    @staticmethod
    def generate_random_id():
        """Generate a random ID for Cognito resources."""
        return str(uuid.uuid4())[:8]

    def create_oauth_authorizer_with_cognito(self, gateway_name: str) -> Dict[str, Any]:
        """Creates Cognito OAuth authorization server.

        Note: This implementation uses AdminCreateUserOnly mode where only administrators
        can create user accounts. If modifying this implementation for public clients,
        review AWS Cognito security best practices regarding user sign-up policies.

        :param gateway_name: the name of the gateway being created for use in naming Cognito resources.
        :return: dictionary with details of the authorization server, client id, and client secret.
        """
        self.logger.info("Starting EZ Auth setup: Creating Cognito resources...")

        cognito_client = self.session.client("cognito-idp")

        try:
            # 1. Create User Pool
            pool_name = f"agentcore-gateway-{GatewayClient.generate_random_id()}"
            user_pool_response = cognito_client.create_user_pool(
                PoolName=pool_name,
                AdminCreateUserConfig={
                    "AllowAdminCreateUserOnly": True  # Disables self-registration
                },
            )
            user_pool_id = user_pool_response["UserPool"]["Id"]
            self.logger.info("  ✓ Created User Pool: %s", user_pool_id)

            # 2. Create User Pool Domain
            domain_prefix = f"agentcore-{GatewayClient.generate_random_id()}"
            cognito_client.create_user_pool_domain(Domain=domain_prefix, UserPoolId=user_pool_id)
            self.logger.info("  ✓ Created domain: %s", domain_prefix)

            # Wait for domain to be available
            self.logger.info("  ⏳ Waiting for domain to be available...")
            domain_ready = False
            for _ in range(30):  # Wait up to 30 seconds
                try:
                    response = cognito_client.describe_user_pool_domain(Domain=domain_prefix)
                    if response.get("DomainDescription", {}).get("Status") == "ACTIVE":
                        domain_ready = True
                        break
                except cognito_client.exceptions.ClientError as e:
                    self.logger.debug("Domain not yet active: %s", e)
                    pass
                time.sleep(1)

            if not domain_ready:
                self.logger.warning("  ⚠️  Domain may not be fully available yet")
            else:
                self.logger.info("  ✓ Domain is active")

            # 3. Create Resource Server
            # Using gateway_name as the resource server identifier
            resource_server_id = gateway_name
            gateway_scopes = [
                {
                    "ScopeName": "invoke",  # Just 'invoke', will be formatted as resource_server_id/invoke
                    "ScopeDescription": "Scope for invoking the agentcore gateway",
                }
            ]

            cognito_client.create_resource_server(
                UserPoolId=user_pool_id,
                Identifier=resource_server_id,
                Name=gateway_name,
                Scopes=gateway_scopes,
            )
            self.logger.info("  ✓ Created resource server: %s", resource_server_id)

            # 4. Create User Pool Client
            client_name = f"agentcore-client-{GatewayClient.generate_random_id()}"

            # Format scopes as {resource_server_id}/{scope_name} as per the update
            scope_names = [f"{resource_server_id}/{scope['ScopeName']}" for scope in gateway_scopes]
            # This results in: "gateway_name/invoke"

            user_pool_client_response = cognito_client.create_user_pool_client(
                UserPoolId=user_pool_id,
                ClientName=client_name,
                GenerateSecret=True,
                AllowedOAuthFlows=["client_credentials"],
                AllowedOAuthScopes=scope_names,  # Using the formatted scope names
                AllowedOAuthFlowsUserPoolClient=True,
                SupportedIdentityProviders=["COGNITO"],
            )

            client_id = user_pool_client_response["UserPoolClient"]["ClientId"]
            client_secret = user_pool_client_response["UserPoolClient"]["ClientSecret"]
            self.logger.info("  ✓ Created client: %s", client_id)

            # Build the return structure
            discovery_url = (
                f"https://cognito-idp.{self.region}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration"
            )

            # Format for AgentCore Gateway authorizer config
            custom_jwt_authorizer = {
                "customJWTAuthorizer": {
                    "allowedClients": [client_id],
                    "discoveryUrl": discovery_url,
                }
            }

            result = {
                "authorizer_config": custom_jwt_authorizer,
                "client_info": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "user_pool_id": user_pool_id,
                    "token_endpoint": f"https://{domain_prefix}.auth.{self.region}.amazoncognito.com/oauth2/token",
                    "scope": scope_names[0],
                    "domain_prefix": domain_prefix,
                },
            }

            if domain_prefix:
                self.logger.info(
                    "  ⏳ Waiting for DNS propagation of domain: %s.auth.%s.amazoncognito.com",
                    domain_prefix,
                    self.region,
                )
                # Wait for DNS to propagate (60 seconds)
                time.sleep(60)

            self.logger.info("✓ EZ Auth setup complete!")
            return result

        except Exception as e:
            raise GatewaySetupException(f"Failed to create Cognito resources: {e}") from e

    def get_access_token_for_cognito(self, client_info: Dict[str, Any]) -> str:
        """Get OAuth token using client credentials flow.

        :param client_info: credentials and context needed to get the access token
                            (output of the create_oauth_authorizer_with_cognito method).
        :return: the access token.
        """
        self.logger.info("Fetching test token from Cognito...")

        max_retries = 5
        retry_delay = 10

        for attempt in range(max_retries):
            try:
                # Make HTTP request to token endpoint
                http = urllib3.PoolManager()

                # Prepare the form data
                form_data = {
                    "grant_type": "client_credentials",
                    "client_id": client_info["client_id"],
                    "client_secret": client_info["client_secret"],
                    "scope": client_info["scope"],
                }

                # Log token endpoint for debugging
                self.logger.info(
                    "  Attempting to connect to token endpoint: %s",
                    client_info["token_endpoint"],
                )

                response = http.request(
                    "POST",
                    client_info["token_endpoint"],
                    body=urllib.parse.urlencode(form_data),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=10.0,  # Add explicit timeout
                    retries=False,
                )

                if response.status != 200:
                    raise GatewaySetupException(f"Token request failed: {response.data.decode()}")

                token_data = json.loads(response.data.decode())
                access_token = token_data["access_token"]

                self.logger.info("✓ Got test token successfully")
                return access_token

            except urllib3.exceptions.MaxRetryError as e:
                if "NameResolutionError" in str(e) and attempt < max_retries - 1:
                    self.logger.warning(
                        "  Domain not yet resolvable (attempt %s/%s). Waiting %s seconds...",
                        attempt + 1,
                        max_retries,
                        retry_delay,
                    )
                    time.sleep(retry_delay)
                    continue
                raise GatewaySetupException(f"Failed to get test token: {e}") from e
            except Exception as e:
                raise GatewaySetupException(f"Failed to get test token: {e}") from e
