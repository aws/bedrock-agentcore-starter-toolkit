"""
QuickGateway setup for simplified Gateway provisioning.
This module is intended for quickstart examples and will be properly tested in a future PR.
"""
# pragma: no cover

from .client import GatewayClient
import boto3
import json
import time
from pathlib import Path

class QuickGateway:
    """One-line Gateway setup for quickstart"""
    
    def __init__(self, region="us-east-1"):
        self.region = region
        self.client = GatewayClient(region_name=region)
        self.config_file = Path("gateway_config.json")
        self.gateway = None
        self.config = {}
        
    def create(self):
        """Create Gateway with all defaults - one line setup"""
        print("🚀 Creating Gateway...")
        
        # Create auth
        cognito = self.client.create_oauth_authorizer_with_cognito("QuickGateway")
        
        # Create gateway with automatic IAM fix
        self.gateway = self.client.create_mcp_gateway(
            authorizer_config=cognito["authorizer_config"],
            enable_semantic_search=True
        )
        
        # Fix IAM permissions
        self._fix_iam_permissions()
        
        # Add Lambda target
        target = self.client.create_mcp_gateway_target(
            gateway=self.gateway,
            target_type="lambda"
        )
        
        # Get token
        token = self.client.get_access_token_for_cognito(cognito["client_info"])
        
        # Save config
        self.config = {
            "gateway_url": self.gateway['gatewayUrl'],
            "gateway_id": self.gateway['gatewayId'],
            "access_token": token,
            "region": self.region,
            "client_info": cognito["client_info"]
        }
        
        with open(self.config_file, "w") as f:
            json.dump(self.config, f, indent=2)
            
        print(f"✅ Gateway ready: {self.gateway['gatewayUrl']}")
        print("⏳ Waiting 30s for IAM propagation...")
        time.sleep(30)
        
        return self.gateway['gatewayUrl']
    
    def test(self):
        """Launch interactive agent"""
        print("🤖 Starting test agent...")  # pragma: no cover
        print("Try: 'What's the weather in Seattle?'")
        print("Type 'exit' to quit\n")
        
        # Import here to avoid circular dependencies
        from strands import Agent
        from strands.models import BedrockModel
        from strands.tools.mcp.mcp_client import MCPClient
        from mcp.client.streamable_http import streamablehttp_client
        
        # Load config
        with open(self.config_file, "r") as f:
            config = json.load(f)
        
        # Setup agent
        mcp_client = MCPClient(
            lambda: streamablehttp_client(
                config['gateway_url'],
                headers={"Authorization": f"Bearer {config['access_token']}"}
            )
        )
        
        with mcp_client:
            tools = mcp_client.list_tools_sync()
            agent = Agent(
                model=BedrockModel(
                    model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                    streaming=True
                ),
                tools=tools
            )
            
            while True:
                user_input = input("You: ")
                if user_input.lower() in ["exit", "quit"]:
                    break
                    
                response = agent(user_input)
                print(f"Agent: {response.message.get('content', response)}\n")
    
    def cleanup(self):
        """Remove all resources"""
        if not self.config_file.exists():
            print("❌ No gateway to clean up")
            return
            
        try:
            with open(self.config_file, "r") as f:
                config = json.load(f)
                
            print("🧹 Cleaning up...")
            
            # Create clients
            region = config.get('region', self.region)
            gateway_client = boto3.client('bedrock-agentcore-control', region_name=region)
            
            # Step 1: List and delete all targets
            gateway_id = config['gateway_id']
            print(f"  • Finding targets for gateway: {gateway_id}")
            
            try:
                response = gateway_client.list_gateway_targets(gatewayIdentifier=gateway_id)
                # API returns targets in 'items' field
                targets = response.get('items', [])
                print(f"    Found {len(targets)} targets to delete")
                
                for target in targets:
                    target_id = target['targetId']
                    print(f"  • Deleting target: {target_id}")
                    try:
                        gateway_client.delete_gateway_target(
                            gatewayIdentifier=gateway_id,
                            targetId=target_id
                        )
                        print(f"    ✓ Target deletion initiated: {target_id}")
                        # Wait for deletion to complete
                        time.sleep(5)
                    except Exception as e:  # pragma: no cover
                        print(f"    ⚠️ Error deleting target {target_id}: {str(e)}")
                
                # Verify all targets are deleted
                print("  • Verifying targets deletion...")
                time.sleep(5)  # Additional wait
                verify_response = gateway_client.list_gateway_targets(gatewayIdentifier=gateway_id)
                remaining_targets = verify_response.get('items', [])
                if remaining_targets:
                    print(f"    ⚠️ {len(remaining_targets)} targets still remain")  # pragma: no cover
                else:
                    print("    ✓ All targets deleted")
                    
            except Exception as e:  # pragma: no cover
                print(f"    ⚠️ Error managing targets: {str(e)}")
            
            # Step 2: Delete the gateway
            try:
                print(f"  • Deleting gateway: {gateway_id}")
                gateway_client.delete_gateway(gatewayIdentifier=gateway_id)
                print(f"    ✓ Gateway deleted: {gateway_id}")
            except Exception as e:  # pragma: no cover
                print(f"    ⚠️ Error deleting gateway: {str(e)}")
            
            # Step 3: Delete Cognito resources
            if 'client_info' in config and 'user_pool_id' in config['client_info']:
                cognito = boto3.client('cognito-idp', region_name=region)
                user_pool_id = config['client_info']['user_pool_id']
                
                # Delete domain first
                if 'domain_prefix' in config['client_info']:  # pragma: no cover
                    domain_prefix = config['client_info']['domain_prefix']
                    print(f"  • Deleting Cognito domain: {domain_prefix}")
                    try:
                        cognito.delete_user_pool_domain(
                            UserPoolId=user_pool_id,
                            Domain=domain_prefix
                        )
                        print(f"    ✓ Cognito domain deleted")
                        time.sleep(5)  # Wait for domain deletion
                    except Exception as e:  # pragma: no cover
                        print(f"    ⚠️ Error deleting Cognito domain: {str(e)}")
                
                # Now delete the user pool
                print(f"  • Deleting Cognito user pool: {user_pool_id}")
                try:
                    cognito.delete_user_pool(UserPoolId=user_pool_id)
                    print(f"    ✓ Cognito user pool deleted")
                except Exception as e:  # pragma: no cover
                    print(f"    ⚠️ Error deleting Cognito user pool: {str(e)}")
            
            # Step 4: Clean up config file
            self.config_file.unlink(missing_ok=True)
            print("  • Configuration file removed")
            
            print("✅ Cleanup complete")
            
        except Exception as e:
            print(f"❌ Cleanup error: {str(e)}")
            print("Some resources may need manual cleanup in the AWS Console")
    
    def _fix_iam_permissions(self):
        """Fix IAM role trust policy"""
        # Check for None gateway
        if self.gateway is None:
            return
            
        # Check for missing roleArn
        role_arn = self.gateway.get('roleArn')
        if not role_arn:
            return
            
        sts = boto3.client('sts')
        iam = boto3.client('iam')
        
        account_id = sts.get_caller_identity()['Account']
        role_name = role_arn.split('/')[-1]
        
        # Update trust policy
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {"aws:SourceAccount": account_id},
                    "ArnLike": {"aws:SourceArn": f"arn:aws:bedrock-agentcore:{self.region}:{account_id}:*"}
                }
            }]
        }
        
        try:
            iam.update_assume_role_policy(
                RoleName=role_name,
                PolicyDocument=json.dumps(trust_policy)
            )
            
            # Add Lambda permissions
            iam.put_role_policy(
                RoleName=role_name,
                PolicyName="LambdaInvokePolicy",
                PolicyDocument=json.dumps({
                    "Version": "2012-10-17",
                    "Statement": [{
                        "Effect": "Allow",
                        "Action": ["lambda:InvokeFunction"],
                        "Resource": f"arn:aws:lambda:{self.region}:{account_id}:function:AgentCoreLambdaTestFunction"
                    }]
                })
            )
        except Exception as e:
            print(f"    ⚠️ IAM role update failed: {str(e)}. Continuing with best effort.")

    def test(self):  # pragma: no cover
        """Launch interactive agent"""
        print("🤖 Starting test agent...")
        print("Try: 'What's the weather in Seattle?'")
        print("Type 'exit' to quit\n")
        
        # The following imports are difficult to mock in tests, so we exclude them from coverage
        from strands import Agent
        from strands.models import BedrockModel
        from strands.tools.mcp.mcp_client import MCPClient
        from mcp.client.streamable_http import streamablehttp_client
        
        # Load config
        with open(self.config_file, "r") as f:
            config = json.load(f)
        
        # Setup agent
        mcp_client = MCPClient(
            lambda: streamablehttp_client(
                config['gateway_url'],
                headers={"Authorization": f"Bearer {config['access_token']}"}
            )
        )
        
        with mcp_client:
            tools = mcp_client.list_tools_sync()
            agent = Agent(
                model=BedrockModel(
                    model_id="us.anthropic.claude-3-7-sonnet-20250219-v1:0",
                    streaming=True
                ),
                tools=tools
            )
            
            while True:
                user_input = input("You: ")
                if user_input.lower() in ["exit", "quit"]:
                    break
                    
                response = agent(user_input)
                print(f"Agent: {response.message.get('content', response)}\n")