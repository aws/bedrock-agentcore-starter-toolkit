"""Launch operation - deploys Bedrock AgentCore locally or to cloud."""

import json
import logging
import time
import urllib.parse
from pathlib import Path
from typing import List, Optional

import boto3
from botocore.exceptions import ClientError
from rich.console import Console

from ...services.codebuild import CodeBuildService
from ...services.ecr import deploy_to_ecr, get_or_create_ecr_repository
from ...services.runtime import BedrockAgentCoreClient
from ...services.xray import enable_transaction_search_if_needed
from ...utils.runtime.config import load_config, save_config
from ...utils.runtime.container import ContainerRuntime
from ...utils.runtime.entrypoint import build_entrypoint_array
from ...utils.runtime.logs import get_genai_observability_url
from ...utils.runtime.schema import BedrockAgentCoreAgentSchema, BedrockAgentCoreConfigSchema
from .create_role import get_or_create_runtime_execution_role
from .exceptions import RuntimeToolkitException
from .models import LaunchResult

# console = Console()

log = logging.getLogger(__name__)


def _validate_vpc_resources(session: boto3.Session, agent_config, region: str) -> None:
    """Validate VPC resources exist and are in the same VPC.

    Args:
        session: Boto3 session
        agent_config: Agent configuration
        region: AWS region

    Raises:
        ValueError: If validation fails
    """
    network_config = agent_config.aws.network_configuration

    if network_config.network_mode != "VPC":
        return  # Nothing to validate for PUBLIC mode

    if not network_config.network_mode_config:
        raise ValueError("VPC mode requires network configuration")

    subnets = network_config.network_mode_config.subnets
    security_groups = network_config.network_mode_config.security_groups

    if not subnets or not security_groups:
        raise ValueError("VPC mode requires both subnets and security groups")

    ec2_client = session.client("ec2", region_name=region)

    # Validate subnets exist and get their VPC IDs
    try:
        subnet_response = ec2_client.describe_subnets(SubnetIds=subnets)
        subnet_vpcs = {subnet["VpcId"] for subnet in subnet_response["Subnets"]}

        if len(subnet_vpcs) > 1:
            raise ValueError(
                f"All subnets must be in the same VPC. "
                f"Found subnets in {len(subnet_vpcs)} different VPCs: {subnet_vpcs}"
            )

        vpc_id = subnet_vpcs.pop()
        log.info("✓ All %d subnets are in VPC: %s", len(subnets), vpc_id)

    except ClientError as e:
        if e.response["Error"]["Code"] == "InvalidSubnetID.NotFound":
            raise ValueError(f"One or more subnet IDs not found: {subnets}") from e
        raise ValueError(f"Failed to validate subnets: {e}") from e

    # Validate security groups exist and are in the same VPC
    try:
        sg_response = ec2_client.describe_security_groups(GroupIds=security_groups)
        sg_vpcs = {sg["VpcId"] for sg in sg_response["SecurityGroups"]}

        if len(sg_vpcs) > 1:
            raise ValueError(
                f"All security groups must be in the same VPC. Found {len(sg_vpcs)} different VPCs: {sg_vpcs}"
            )

        sg_vpc_id = sg_vpcs.pop()

        if sg_vpc_id != vpc_id:
            raise ValueError(
                f"Security groups must be in the same VPC as subnets. "
                f"Subnets are in VPC {vpc_id}, but security groups are in VPC {sg_vpc_id}"
            )

        log.info("✓ All %d security groups are in VPC: %s", len(security_groups), vpc_id)

    except ClientError as e:
        if e.response["Error"]["Code"] == "InvalidGroup.NotFound":
            raise ValueError(f"One or more security group IDs not found: {security_groups}") from e
        raise ValueError(f"Failed to validate security groups: {e}") from e

    log.info("✓ VPC configuration validated successfully")


def _ensure_network_service_linked_role(session: boto3.Session, logger) -> None:
    """Ensure the AgentCore Network service-linked role exists."""
    iam_client = session.client("iam")
    role_name = "AWSServiceRoleForBedrockAgentCoreNetwork"

    try:
        # Check if role exists
        iam_client.get_role(RoleName=role_name)
        logger.info("✓ VPC service-linked role verified: %s", role_name)

    except ClientError as e:
        if e.response["Error"]["Code"] != "NoSuchEntity":
            raise

        logger.info("Creating VPC service-linked role...")

        try:
            iam_client.create_service_linked_role(
                AWSServiceName="network.bedrock-agentcore.amazonaws.com",
                Description="Service-linked role for Amazon Bedrock AgentCore VPC networking",
            )
            logger.info("✓ VPC service-linked role created: %s", role_name)

            # Wait for propagation
            import time

            logger.info("  Waiting 10 seconds for IAM propagation...")
            time.sleep(10)

        except ClientError as e:
            if e.response["Error"]["Code"] == "InvalidInput":
                logger.info("✓ VPC service-linked role verified (created by another process)")
            else:
                logger.error("✗ Failed to create service-linked role: %s", e)
                raise


def _ensure_ecr_repository(agent_config, project_config, config_path, agent_name, region):
    """Ensure ECR repository exists (idempotent)."""
    ecr_uri = agent_config.aws.ecr_repository

    # Step 1: Check if we already have a repository in config
    if ecr_uri:
        log.info("Using ECR repository from config: %s", ecr_uri)
        return ecr_uri

    # Step 2: Create repository if needed (idempotent)
    if agent_config.aws.ecr_auto_create:
        log.info("Getting or creating ECR repository for agent: %s", agent_name)

        ecr_uri = get_or_create_ecr_repository(agent_name, region)

        # Update the config
        agent_config.aws.ecr_repository = ecr_uri
        agent_config.aws.ecr_auto_create = False

        # Update the project config and save
        project_config.agents[agent_config.name] = agent_config
        save_config(project_config, config_path)

        log.info("ECR repository available: %s", ecr_uri)
        return ecr_uri

    # Step 3: No repository and auto-create disabled
    raise ValueError("ECR repository not configured and auto-create not enabled")


def _validate_execution_role(role_arn: str, session: boto3.Session) -> bool:
    """Validate that execution role exists and has correct trust policy for Bedrock AgentCore."""
    iam = session.client("iam")
    role_name = role_arn.split("/")[-1]

    try:
        response = iam.get_role(RoleName=role_name)
        trust_policy = response["Role"]["AssumeRolePolicyDocument"]

        # Parse trust policy (it might be URL-encoded)
        if isinstance(trust_policy, str):
            trust_policy = json.loads(urllib.parse.unquote(trust_policy))

        # Check if bedrock-agentcore service can assume this role
        for statement in trust_policy.get("Statement", []):
            if statement.get("Effect") == "Allow":
                principals = statement.get("Principal", {})

                if isinstance(principals, dict):
                    services = principals.get("Service", [])
                    if isinstance(services, str):
                        services = [services]

                    if "bedrock-agentcore.amazonaws.com" in services:
                        return True

        return False

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchEntity":
            return False
        raise


def _ensure_execution_role(agent_config, project_config, config_path, agent_name, region, account_id):
    """Ensure execution role exists without waiting.

    This function handles:
    1. Reusing existing role from config if available
    2. Creating role if needed (auto_create_execution_role=True) - now idempotent
    3. Basic validation that existing roles have correct trust policy
    4. Returning role ARN (readiness will be checked during actual deployment)
    """
    execution_role_arn = agent_config.aws.execution_role
    session = boto3.Session(region_name=region)

    # Step 1: Check if we already have a role in config
    if execution_role_arn:
        log.info("Using execution role from config: %s", execution_role_arn)
        return execution_role_arn

    # Step 3: Create role if needed (idempotent)
    if agent_config.aws.execution_role_auto_create:
        execution_role_arn = get_or_create_runtime_execution_role(
            session=session,
            logger=log,
            region=region,
            account_id=account_id,
            agent_name=agent_name,
        )

        # Update the config
        agent_config.aws.execution_role = execution_role_arn
        agent_config.aws.execution_role_auto_create = False

        # Update the project config and save
        project_config.agents[agent_config.name] = agent_config
        save_config(project_config, config_path)

        log.info("Execution role available: %s", execution_role_arn)
        return execution_role_arn

    # Step 4: No role and auto-create disabled
    raise ValueError("Execution role not configured and auto-create not enabled")


def _ensure_memory_for_agent(
    agent_config: BedrockAgentCoreAgentSchema,
    project_config: BedrockAgentCoreConfigSchema,
    config_path: Path,
    agent_name: str,
    console: Optional[Console] = None,
) -> Optional[str]:
    """Ensure memory resource exists for agent. Returns memory_id or None.

    This function is idempotent - it creates memory if needed or reuses existing.
    CRITICAL: Never overwrites was_created_by_toolkit flag - that's set by configure.
    """
    # Check if memory is disabled
    if agent_config.memory and agent_config.memory.mode == "NO_MEMORY":
        log.info("Memory disabled - skipping memory creation")
        return None

    # If memory already exists, return it
    if agent_config.memory and agent_config.memory.memory_id:
        log.info("Using existing memory: %s", agent_config.memory.memory_id)
        return agent_config.memory.memory_id

    # If memory not enabled, skip
    if not agent_config.memory or not agent_config.memory.is_enabled:
        return None

    log.info("Creating memory resource for agent: %s", agent_name)
    try:
        from ...operations.memory.constants import StrategyType
        from ...operations.memory.manager import MemoryManager

        memory_manager = MemoryManager(
            region_name=agent_config.aws.region,
            console=console,  # ADD THIS
        )
        memory_name = f"{agent_name}_mem"  # Short name under 48 char limit

        # Check if memory already exists in cloud
        existing_memory = None
        try:
            memories = memory_manager.list_memories()
            for m in memories:
                if m.id.startswith(memory_name):
                    existing_memory = memory_manager.get_memory(m.id)
                    log.info("Found existing memory in cloud: %s", m.id)
                    # DO NOT OVERWRITE was_created_by_toolkit flag
                    # The flag from configure tells us the user's intent
                    break
        except Exception as e:
            log.debug("Error checking for existing memory: %s", e)

        # Determine if we need to create new memory or add strategies to existing
        if existing_memory:
            # Check if strategies need to be added
            existing_strategies = []
            if hasattr(existing_memory, "strategies") and existing_memory.strategies:
                existing_strategies = existing_memory.strategies

            log.info("Existing memory has %d strategies", len(existing_strategies))

            # If LTM is enabled but no strategies exist, add them
            if agent_config.memory.has_ltm and len(existing_strategies) == 0:
                log.info("Adding LTM strategies to existing memory...")
                log.info("⏳ Adding long-term memory strategies (this may take 30-180 seconds)...")
                memory_manager.update_memory_strategies_and_wait(
                    memory_id=existing_memory.id,
                    add_strategies=[
                        {
                            StrategyType.USER_PREFERENCE.value: {
                                "name": "UserPreferences",
                                "namespaces": ["/users/{actorId}/preferences"],
                            }
                        },
                        {
                            StrategyType.SEMANTIC.value: {
                                "name": "SemanticFacts",
                                "namespaces": ["/users/{actorId}/facts"],
                            }
                        },
                        {
                            StrategyType.SUMMARY.value: {
                                "name": "SessionSummaries",
                                "namespaces": ["/summaries/{actorId}/{sessionId}"],
                            }
                        },
                    ],
                    max_wait=300,  # CHANGE: Increased from 30 to 300
                    poll_interval=5,
                )
                memory = existing_memory
                log.info("LTM strategies added to existing memory")
            else:
                # CHANGE: ADD THIS BLOCK - Wait for existing memory to become ACTIVE
                log.info("⏳ Waiting for existing memory to become ACTIVE...")
                memory = memory_manager._wait_for_memory_active(
                    existing_memory.id,
                    max_wait=300,
                    poll_interval=5,
                )
                # END CHANGE

                if agent_config.memory.has_ltm and len(existing_strategies) > 0:
                    log.info("Using existing memory with %d strategies", len(existing_strategies))
                else:
                    log.info("Using existing STM-only memory")
        else:
            # Create new memory with appropriate strategies
            strategies = []
            if agent_config.memory.has_ltm:
                log.info("Creating new memory with LTM strategies...")
                strategies = [
                    {
                        StrategyType.USER_PREFERENCE.value: {
                            "name": "UserPreferences",
                            "namespaces": ["/users/{actorId}/preferences"],
                        }
                    },
                    {
                        StrategyType.SEMANTIC.value: {
                            "name": "SemanticFacts",
                            "namespaces": ["/users/{actorId}/facts"],
                        }
                    },
                    {
                        StrategyType.SUMMARY.value: {
                            "name": "SessionSummaries",
                            "namespaces": ["/summaries/{actorId}/{sessionId}"],
                        }
                    },
                ]
            else:
                log.info("Creating new STM-only memory...")

            # CHANGE: Use create_memory_and_wait instead of _create_memory
            log.info("⏳ Creating memory resource (this may take 30-180 seconds)...")
            memory = memory_manager.create_memory_and_wait(
                name=memory_name,
                description=f"Memory for agent {agent_name} with {'STM+LTM' if strategies else 'STM only'}",
                strategies=strategies,
                event_expiry_days=agent_config.memory.event_expiry_days or 30,
                max_wait=300,  # 5 minutes
                poll_interval=5,
            )
            log.info("Memory created and active: %s", memory.id)
            # END CHANGE

            # CHANGE: ADD THIS - Mark as created by toolkit since we just created it
            if not agent_config.memory.was_created_by_toolkit:
                agent_config.memory.was_created_by_toolkit = True
            # END CHANGE

        # Save memory configuration (preserving was_created_by_toolkit flag)
        agent_config.memory.memory_id = memory.id
        agent_config.memory.memory_arn = memory.arn
        agent_config.memory.memory_name = memory_name
        agent_config.memory.first_invoke_memory_check_done = True  # CHANGE: Set to True since memory is now ACTIVE

        project_config.agents[agent_config.name] = agent_config
        save_config(project_config, config_path)

        return memory.id

    except Exception as e:
        log.error("Memory creation failed: %s", str(e))
        log.warning("Continuing without memory.")
        return None


def _deploy_to_bedrock_agentcore(
    agent_config: BedrockAgentCoreAgentSchema,
    project_config: BedrockAgentCoreConfigSchema,
    config_path: Path,
    agent_name: str,
    ecr_uri: str,
    region: str,
    account_id: str,
    env_vars: Optional[dict] = None,
    auto_update_on_conflict: bool = False,
):
    """Deploy agent to Bedrock AgentCore with retry logic for role validation."""
    log.info("Deploying to Bedrock AgentCore...")

    # Prepare environment variables
    if env_vars is None:
        env_vars = {}

    # Add memory configuration to env_vars only if memory is enabled
    if agent_config.memory and agent_config.memory.mode != "NO_MEMORY" and agent_config.memory.memory_id:
        env_vars["BEDROCK_AGENTCORE_MEMORY_ID"] = agent_config.memory.memory_id
        env_vars["BEDROCK_AGENTCORE_MEMORY_NAME"] = agent_config.memory.memory_name
        log.info("Passing memory configuration to agent: %s", agent_config.memory.memory_id)

    bedrock_agentcore_client = BedrockAgentCoreClient(region)

    # Transform network configuration to AWS API format
    network_config = agent_config.aws.network_configuration.to_aws_dict()
    protocol_config = agent_config.aws.protocol_configuration.to_aws_dict()

    lifecycle_config = None
    if agent_config.aws.lifecycle_configuration.has_custom_settings:
        lifecycle_config = agent_config.aws.lifecycle_configuration.to_aws_dict()
        log.info(
            "Applying custom lifecycle settings: idle=%s, max=%s",
            agent_config.aws.lifecycle_configuration.idle_runtime_session_timeout,
            agent_config.aws.lifecycle_configuration.max_lifetime,
        )

    # Execution role should be available by now (either provided or auto-created)
    if not agent_config.aws.execution_role:
        raise ValueError(
            "Execution role not available. This should have been handled by _ensure_execution_role. "
            "Please check configuration or enable auto-creation."
        )

    # Retry logic for role validation eventual consistency
    max_retries = 3
    base_delay = 5  # Start with 2 seconds
    max_delay = 15  # Max 32 seconds between retries

    for attempt in range(max_retries + 1):
        try:
            agent_info = bedrock_agentcore_client.create_or_update_agent(
                agent_id=agent_config.bedrock_agentcore.agent_id,
                agent_name=agent_name,
                execution_role_arn=agent_config.aws.execution_role,
                deployment_type="container",
                image_uri=f"{ecr_uri}:latest",
                network_config=network_config,
                authorizer_config=agent_config.get_authorizer_configuration(),
                request_header_config=agent_config.request_header_configuration,
                protocol_config=protocol_config,
                env_vars=env_vars,
                auto_update_on_conflict=auto_update_on_conflict,
                lifecycle_config=lifecycle_config,
            )
            break  # Success! Exit retry loop

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            error_message = e.response.get("Error", {}).get("Message", "")

            # Check if this is a role validation error
            is_role_validation_error = (
                error_code == "ValidationException"
                and "Role validation failed" in error_message
                and agent_config.aws.execution_role in error_message
            )

            if not is_role_validation_error or attempt == max_retries:
                # Not a role validation error, or we've exhausted retries
                if is_role_validation_error:
                    log.error(
                        "Role validation failed after %d attempts. The execution role may not be ready. Role: %s",
                        max_retries + 1,
                        agent_config.aws.execution_role,
                    )
                raise e

            # Calculate delay with exponential backoff
            delay = min(base_delay * (2**attempt), max_delay)
            log.info(
                "⏳ Role validation failed (attempt %d/%d), retrying in %ds... Role: %s",
                attempt + 1,
                max_retries + 1,
                delay,
                agent_config.aws.execution_role,
            )
            time.sleep(delay)

    # Save deployment info
    agent_id = agent_info["id"]
    agent_arn = agent_info["arn"]

    # Update the config
    agent_config.bedrock_agentcore.agent_id = agent_id
    agent_config.bedrock_agentcore.agent_arn = agent_arn

    # Reset session id if present
    existing_session_id = agent_config.bedrock_agentcore.agent_session_id
    if existing_session_id is not None:
        log.warning(
            "⚠️ Session ID will be reset to connect to the updated agent. "
            "The previous agent remains accessible via the original session ID: %s",
            existing_session_id,
        )
        agent_config.bedrock_agentcore.agent_session_id = None

    # Update the project config and save
    project_config.agents[agent_config.name] = agent_config
    save_config(project_config, config_path)

    log.info("Agent created/updated: %s", agent_arn)

    # Enable Transaction Search if observability is enabled
    if agent_config.aws.observability.enabled:
        log.info("Observability is enabled, configuring Transaction Search...")
        enable_transaction_search_if_needed(region, account_id)

        # Show GenAI Observability Dashboard URL whenever OTEL is enabled
        console_url = get_genai_observability_url(region)
        log.info("🔍 GenAI Observability Dashboard:")
        log.info("   %s", console_url)

    # Wait for agent to be ready
    log.info("Polling for endpoint to be ready...")
    result = bedrock_agentcore_client.wait_for_agent_endpoint_ready(agent_id)
    log.info("Agent endpoint: %s", result)

    if agent_config.aws.network_configuration.network_mode == "VPC":
        vpc_subnets = agent_config.aws.network_configuration.network_mode_config.subnets
        session = boto3.Session(region_name=region)
        _check_vpc_deployment(session, agent_id, vpc_subnets, region)

    return agent_id, agent_arn


def _check_vpc_deployment(session: boto3.Session, agent_id: str, vpc_subnets: List[str], region: str) -> None:
    """Verify VPC deployment created ENIs in the specified subnets."""
    ec2_client = session.client("ec2", region_name=region)

    try:
        # Look for ENIs in our subnets with AgentCore description
        response = ec2_client.describe_network_interfaces(
            Filters=[
                {"Name": "subnet-id", "Values": vpc_subnets},
                {"Name": "description", "Values": ["*AgentCore*", "*bedrock-agentcore*"]},
            ]
        )

        all_enis = response.get("NetworkInterfaces", [])
        our_enis = [eni for eni in all_enis if eni.get("SubnetId") in vpc_subnets]

        if our_enis:
            log.info("✓ Found %d ENI(s) in configured subnets:", len(our_enis))
            for eni in our_enis:
                log.info("  - ENI ID: %s", eni["NetworkInterfaceId"])
                log.info("    Subnet: %s", eni["SubnetId"])
                log.info("    Private IP: %s", eni.get("PrivateIpAddress", "N/A"))
                log.info("    Status: %s", eni["Status"])
                log.info("    Security Groups: %s", [sg["GroupId"] for sg in eni.get("Groups", [])])
        else:
            log.info(":information_source:  VPC network interfaces will be created on first invocation")

    except Exception as e:
        log.error("Error checking ENIs: %s", e)


def _launch_direct_code_deploy_local(
    agent_config: BedrockAgentCoreAgentSchema,
    env_vars: Optional[dict],
) -> LaunchResult:
    """Prepare for local direct_code_deploy execution using uv python."""
    import shutil
    from pathlib import Path

    log.info("Preparing local direct_code_deploy execution for agent '%s'", agent_config.name)

    # Validate prerequisites
    if not shutil.which("uv"):
        raise RuntimeError(
            "uv is required for local direct_code_deploy execution but was not found.\n"
            "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
        )

    # Get source directory and entrypoint
    source_dir = Path(agent_config.source_path) if agent_config.source_path else Path.cwd()
    entrypoint_abs = Path(agent_config.entrypoint)

    # Validate entrypoint exists
    if not entrypoint_abs.exists():
        raise RuntimeError(f"Entrypoint file not found: {entrypoint_abs}")

    # Compute relative path from source_dir to entrypoint
    try:
        entrypoint_path = str(entrypoint_abs.relative_to(source_dir))
    except ValueError:
        # If entrypoint is not relative to source_dir, use just the filename
        entrypoint_path = entrypoint_abs.name

    log.info("Using source directory: %s", source_dir)
    log.info("Using entrypoint: %s", entrypoint_path)

    # Prepare environment variables
    local_env = {}
    if env_vars:
        local_env.update(env_vars)

    # Add memory configuration if available
    if agent_config.memory and agent_config.memory.memory_id:
        local_env["BEDROCK_AGENTCORE_MEMORY_ID"] = agent_config.memory.memory_id
        local_env["BEDROCK_AGENTCORE_MEMORY_NAME"] = agent_config.memory.memory_name

    # Set default port
    port = int(local_env.get("PORT", "8080"))

    return LaunchResult(
        mode="local_direct_code_deploy",
        tag=f"direct_code_deploy-{agent_config.name}",
        port=port,
        env_vars=local_env,
    )


def launch_bedrock_agentcore(
    config_path: Path,
    agent_name: Optional[str] = None,
    local: bool = False,
    use_codebuild: bool = True,
    env_vars: Optional[dict] = None,
    auto_update_on_conflict: bool = False,
    console: Optional[Console] = None,
    force_rebuild_deps: bool = False,
) -> LaunchResult:
    """Launch Bedrock AgentCore locally or to cloud.

    Args:
        config_path: Path to BedrockAgentCore configuration file
        agent_name: Name of agent to launch (for project configurations)
        local: Whether to run locally
        use_codebuild: Whether to use CodeBuild for ARM64 builds (container deployments only)
        env_vars: Environment variables to pass to local container (dict of key-value pairs)
        auto_update_on_conflict: Whether to automatically update when agent already exists (default: False)
        console: Optional Rich Console instance for progress output. Used to maintain
                output hierarchy with CLI status contexts.
        force_rebuild_deps: Force rebuild of dependencies (direct_code_deploy deployments only)

    Returns:
        LaunchResult model with launch details
    """
    if console is None:
        console = Console()
    # Load project configuration
    project_config = load_config(config_path)
    agent_config = project_config.get_agent_config(agent_name)

    if env_vars is None:
        env_vars = {}

    if agent_config.aws.network_configuration.network_mode == "VPC":
        if local:
            log.warning("⚠️  VPC configuration detected but running in local mode. VPC settings will be ignored.")
        else:
            log.info("Validating VPC resources...")
            session = boto3.Session(region_name=agent_config.aws.region)
            _validate_vpc_resources(session, agent_config, agent_config.aws.region)

            # Ensure service-linked role exists for VPC networking
            _ensure_network_service_linked_role(session, log)

    # Ensure memory exists for non-CodeBuild paths
    if not use_codebuild:
        _ensure_memory_for_agent(agent_config, project_config, config_path, agent_config.name)
    # Route based on deployment type for cloud deployments
    if not local and agent_config.deployment_type == "direct_code_deploy":
        return _launch_with_direct_code_deploy(
            config_path=config_path,
            agent_config=agent_config,
            project_config=project_config,
            auto_update_on_conflict=auto_update_on_conflict,
            env_vars=env_vars,
            force_rebuild_deps=force_rebuild_deps,
        )

    # Route for local direct_code_deploy deployment
    if local and agent_config.deployment_type == "direct_code_deploy":
        return _launch_direct_code_deploy_local(
            agent_config=agent_config,
            env_vars=env_vars,
        )

    # Ensure memory exists for non-CodeBuild paths
    if not use_codebuild:
        _ensure_memory_for_agent(agent_config, project_config, config_path, agent_config.name, console=console)

    # Add memory configuration to environment variables if available
    if agent_config.memory and agent_config.memory.memory_id:
        env_vars["BEDROCK_AGENTCORE_MEMORY_ID"] = agent_config.memory.memory_id
        env_vars["BEDROCK_AGENTCORE_MEMORY_NAME"] = agent_config.memory.memory_name

    # Handle CodeBuild deployment (container deployments, not for local mode)
    if use_codebuild and not local:
        return _launch_with_codebuild(
            config_path=config_path,
            agent_name=agent_config.name,
            agent_config=agent_config,
            project_config=project_config,
            auto_update_on_conflict=auto_update_on_conflict,
            env_vars=env_vars,
        )

    # Log which agent is being launched
    mode = "locally" if local else "to cloud"
    log.info("Launching Bedrock AgentCore agent '%s' %s", agent_config.name, mode)

    # Validate configuration
    errors = agent_config.validate(for_local=local)
    if errors:
        raise ValueError(f"Invalid configuration: {', '.join(errors)}")

    # Initialize container runtime
    runtime = ContainerRuntime(agent_config.container_runtime)

    # Check if we need local runtime for this operation
    if local and not runtime.has_local_runtime:
        raise RuntimeError(
            "Cannot run locally - no container runtime available\n"
            "💡 Recommendation: Use CodeBuild for cloud deployment\n"
            "💡 Run 'agentcore launch' (without --local) for CodeBuild deployment\n"
            "💡 For local runs, please install Docker, Finch, or Podman"
        )

    # Check if we need local runtime for local-build mode (cloud deployment with local build)
    if not local and not use_codebuild and not runtime.has_local_runtime:
        raise RuntimeError(
            "Cannot build locally - no container runtime available\n"
            "💡 Recommendation: Use CodeBuild for cloud deployment (no Docker needed)\n"
            "💡 Run 'agentcore launch' (without --local-build) for CodeBuild deployment\n"
            "💡 For local builds, please install Docker, Finch, or Podman"
        )

    # Get build context - use source_path if configured, otherwise use project root
    build_dir = Path(agent_config.source_path) if agent_config.source_path else config_path.parent
    log.info("Using build directory: %s", build_dir)

    bedrock_agentcore_name = agent_config.name
    tag = f"bedrock_agentcore-{bedrock_agentcore_name}:latest"

    # Step 1: Build Docker image (only if we need it)
    # When using source_path, Dockerfile is in .bedrock_agentcore/{agent_name}/ directory
    from ...utils.runtime.config import get_agentcore_directory

    dockerfile_dir = get_agentcore_directory(config_path.parent, agent_config.name, agent_config.source_path)
    dockerfile_path = dockerfile_dir / "Dockerfile"

    if not dockerfile_path.exists():
        raise RuntimeError(f"Dockerfile not found at {dockerfile_path}. Please run 'agentcore configure' first.")

    success, output = runtime.build(build_dir, tag, dockerfile_path=dockerfile_path)
    if not success:
        error_lines = output[-10:] if len(output) > 10 else output
        error_message = " ".join(error_lines)

        # Check if this is a container runtime issue and suggest CodeBuild
        if "No container runtime available" in error_message:
            raise RuntimeError(
                f"Build failed: {error_message}\n"
                "💡 Recommendation: Use CodeBuild for building containers in the cloud\n"
                "💡 Run 'agentcore launch' (default) for CodeBuild deployment"
            )
        else:
            raise RuntimeError(f"Build failed: {error_message}")

    log.info("Docker image built: %s", tag)

    if local:
        # Return info for local deployment
        return LaunchResult(
            mode="local",
            tag=tag,
            port=8080,
            runtime=runtime,
            env_vars=env_vars,
        )

    region = agent_config.aws.region
    if not region:
        raise ValueError("Region not found in configuration")

    account_id = agent_config.aws.account

    # Step 2: Ensure execution role exists (moved before ECR push)
    _ensure_execution_role(agent_config, project_config, config_path, bedrock_agentcore_name, region, account_id)

    # Step 3: Push to ECR
    log.info("Uploading to ECR...")

    # Handle ECR repository
    ecr_uri = _ensure_ecr_repository(agent_config, project_config, config_path, bedrock_agentcore_name, region)

    # Deploy to ECR
    repo_name = "/".join(ecr_uri.split("/")[1:])
    deploy_to_ecr(tag, repo_name, region, runtime)

    log.info("Image uploaded to ECR: %s", ecr_uri)

    # Step 4: Deploy agent (with retry logic for role readiness)
    agent_id, agent_arn = _deploy_to_bedrock_agentcore(
        agent_config,
        project_config,
        config_path,
        bedrock_agentcore_name,
        ecr_uri,
        region,
        account_id,
        env_vars,
        auto_update_on_conflict,
    )

    return LaunchResult(
        mode="cloud",
        tag=tag,
        agent_arn=agent_arn,
        agent_id=agent_id,
        ecr_uri=ecr_uri,
        build_output=output,
    )


def _execute_codebuild_workflow(
    config_path: Path,
    agent_name: str,
    agent_config,
    project_config,
    ecr_only: bool = False,
    auto_update_on_conflict: bool = False,
    env_vars: Optional[dict] = None,
) -> LaunchResult:
    """Launch using CodeBuild for ARM64 builds."""
    log.info(
        "Starting CodeBuild ARM64 deployment for agent '%s' to account %s (%s)",
        agent_name,
        agent_config.aws.account,
        agent_config.aws.region,
    )

    # Track created resources for error context
    created_resources = []

    try:
        # Validate configuration
        errors = agent_config.validate(for_local=False)
        if errors:
            raise ValueError(f"Invalid configuration: {', '.join(errors)}")

        region = agent_config.aws.region
        if not region:
            raise ValueError("Region not found in configuration")

        session = boto3.Session(region_name=region)
        account_id = agent_config.aws.account  # Use existing account from config

        # Setup AWS resources
        log.info("Setting up AWS resources (ECR repository%s)...", "" if ecr_only else ", execution roles")
        ecr_uri = _ensure_ecr_repository(agent_config, project_config, config_path, agent_name, region)
        if ecr_uri:
            created_resources.append(f"ECR Repository: {ecr_uri}")
        ecr_repository_arn = f"arn:aws:ecr:{region}:{account_id}:repository/{ecr_uri.split('/')[-1]}"

        # Setup execution role only if not ECR-only mode
        if not ecr_only:
            _ensure_execution_role(agent_config, project_config, config_path, agent_name, region, account_id)
            if agent_config.aws.execution_role:
                created_resources.append(f"Runtime Execution Role: {agent_config.aws.execution_role}")

        # Prepare CodeBuild
        log.info("Preparing CodeBuild project and uploading source...")
        codebuild_service = CodeBuildService(session)

        # Use cached CodeBuild role from config if available
        if hasattr(agent_config, "codebuild") and agent_config.codebuild.execution_role:
            log.info("Using CodeBuild role from config: %s", agent_config.codebuild.execution_role)
            codebuild_execution_role = agent_config.codebuild.execution_role
        else:
            codebuild_execution_role = codebuild_service.create_codebuild_execution_role(
                account_id=account_id, ecr_repository_arn=ecr_repository_arn, agent_name=agent_name
            )
            if codebuild_execution_role:
                created_resources.append(f"CodeBuild Execution Role: {codebuild_execution_role}")

        # Get source directory - use source_path if configured, otherwise use current directory
        source_dir = str(Path(agent_config.source_path)) if agent_config.source_path else "."

        # Get Dockerfile directory - use agentcore directory if source_path provided
        from ...utils.runtime.config import get_agentcore_directory

        dockerfile_dir = get_agentcore_directory(config_path.parent, agent_name, agent_config.source_path)

        source_location = codebuild_service.upload_source(
            agent_name=agent_name, source_dir=source_dir, dockerfile_dir=str(dockerfile_dir)
        )

        # Use cached project name from config if available
        if hasattr(agent_config, "codebuild") and agent_config.codebuild.project_name:
            log.info("Using CodeBuild project from config: %s", agent_config.codebuild.project_name)
            project_name = agent_config.codebuild.project_name
        else:
            project_name = codebuild_service.create_or_update_project(
                agent_name=agent_name,
                ecr_repository_uri=ecr_uri,
                execution_role=codebuild_execution_role,
                source_location=source_location,
            )
            if project_name:
                created_resources.append(f"CodeBuild Project: {project_name}")

    except Exception as e:
        if created_resources:
            log.error("Launch failed after creating the following resources: %s. Error: %s", created_resources, str(e))
            raise RuntimeToolkitException("Launch failed", created_resources) from e
        raise

    # Execute CodeBuild
    log.info("Starting CodeBuild build (this may take several minutes)...")
    build_id = codebuild_service.start_build(project_name, source_location)
    codebuild_service.wait_for_completion(build_id)
    log.info("CodeBuild completed successfully")

    # Update CodeBuild config only for full deployments, not ECR-only
    if not ecr_only:
        agent_config.codebuild.project_name = project_name
        agent_config.codebuild.execution_role = codebuild_execution_role
        agent_config.codebuild.source_bucket = codebuild_service.source_bucket

        # Save config changes
        project_config.agents[agent_config.name] = agent_config
        save_config(project_config, config_path)
        log.info("CodeBuild project configuration saved")
    else:
        log.info("ECR-only build completed (project configuration not saved)")

    return build_id, ecr_uri, region, account_id


def _launch_with_codebuild(
    config_path: Path,
    agent_name: str,
    agent_config,
    project_config,
    auto_update_on_conflict: bool = False,
    env_vars: Optional[dict] = None,
    console: Optional[Console] = None,
) -> LaunchResult:
    """Launch using CodeBuild for ARM64 builds."""
    if console is None:
        console = Console()
    # Create memory if configured
    _ensure_memory_for_agent(agent_config, project_config, config_path, agent_name, console=console)

    # Execute shared CodeBuild workflow with full deployment mode
    build_id, ecr_uri, region, account_id = _execute_codebuild_workflow(
        config_path=config_path,
        agent_name=agent_name,
        agent_config=agent_config,
        project_config=project_config,
        ecr_only=False,
        auto_update_on_conflict=auto_update_on_conflict,
        env_vars=env_vars,
    )

    # Deploy to Bedrock AgentCore
    agent_id, agent_arn = _deploy_to_bedrock_agentcore(
        agent_config,
        project_config,
        config_path,
        agent_name,
        ecr_uri,
        region,
        account_id,
        env_vars=env_vars,
        auto_update_on_conflict=auto_update_on_conflict,
    )

    log.info("Deployment completed successfully - Agent: %s", agent_arn)

    return LaunchResult(
        mode="codebuild",
        tag=f"bedrock_agentcore-{agent_name}:latest",
        codebuild_id=build_id,
        ecr_uri=ecr_uri,
        agent_arn=agent_arn,
        agent_id=agent_id,
    )


def _launch_with_direct_code_deploy(
    config_path: Path,
    agent_config: BedrockAgentCoreAgentSchema,
    project_config: BedrockAgentCoreConfigSchema,
    auto_update_on_conflict: bool,
    env_vars: Optional[dict],
    force_rebuild_deps: bool = False,
) -> LaunchResult:
    """Deploy using code zip artifact (Lambda-style deployment).

    Args:
        config_path: Path to configuration file
        agent_config: Agent configuration
        project_config: Project configuration
        auto_update_on_conflict: Whether to auto-update on conflict
        env_vars: Environment variables
        force_rebuild_deps: Force rebuild of dependencies

    Returns:
        LaunchResult with deployment details
    """
    import shutil
    import time

    log.info("Launching with direct_code_deploy deployment for agent '%s'", agent_config.name)

    # Validate configuration
    step_start = time.time()
    errors = agent_config.validate(for_local=False)
    if errors:
        raise ValueError(f"Invalid configuration: {', '.join(errors)}")

    # Validate prerequisites for direct_code_deploy deployment (fail fast before expensive operations)
    if not shutil.which("uv"):
        raise RuntimeError(
            "uv is required for direct_code_deploy deployment but was not found.\n"
            "Install uv: https://docs.astral.sh/uv/getting-started/installation/\n"
            "Or use container deployment instead: agentcore configure --help"
        )
    if not shutil.which("zip"):
        raise RuntimeError(
            "zip utility is required for direct_code_deploy deployment but was not found.\n"
            "Install zip: brew install zip (macOS) or apt-get install zip (Ubuntu)"
        )

    # runtime_type is optional, will default to PYTHON_3_11 in service layer

    region = agent_config.aws.region
    account_id = agent_config.aws.account
    session = boto3.Session(region_name=region)

    # Step 1: Ensure execution role
    step_start = time.time()
    log.info("Ensuring execution role...")
    _ensure_execution_role(agent_config, project_config, config_path, agent_config.name, region, account_id)

    # Step 2: Ensure memory (if configured)
    step_start = time.time()
    _ensure_memory_for_agent(agent_config, project_config, config_path, agent_config.name)

    # Step 3: Prepare entrypoint (compute relative path from source directory)
    step_start = time.time()
    source_dir = Path(agent_config.source_path) if agent_config.source_path else config_path.parent
    entrypoint_abs = Path(agent_config.entrypoint)

    # Compute relative path from source_dir to entrypoint
    try:
        entrypoint_path = str(entrypoint_abs.relative_to(source_dir))
    except ValueError:
        # If entrypoint is not relative to source_dir, use just the filename
        entrypoint_path = entrypoint_abs.name

    log.info("Using entrypoint: %s (relative to %s)", entrypoint_path, source_dir)

    # Step 4: Create deployment package
    step_start = time.time()
    from ...utils.runtime.config import get_agentcore_directory
    from ...utils.runtime.entrypoint import detect_dependencies
    from ...utils.runtime.package import CodeZipPackager

    cache_dir = get_agentcore_directory(config_path.parent, agent_config.name, agent_config.source_path)

    packager = CodeZipPackager()

    # Detect dependencies
    dep_info = detect_dependencies(source_dir)

    log.info("Creating deployment package...")
    deployment_zip, has_otel_distro = packager.create_deployment_package(
        source_dir=source_dir,
        agent_name=agent_config.name,
        cache_dir=cache_dir,
        runtime_version=agent_config.runtime_type,
        requirements_file=Path(dep_info.resolved_path) if dep_info.found else None,
        force_rebuild_deps=force_rebuild_deps,
    )


    try:
        # Initialize variables for direct_code_deploy deployment
        bucket_name = None
        s3_key = None

        # Step 5a: Create S3 bucket if needed (idempotent)
        if agent_config.aws.s3_auto_create:
            from ...services.s3 import get_or_create_s3_bucket

            log.info("Getting or creating S3 bucket for agent: %s", agent_config.name)

            bucket_name = get_or_create_s3_bucket(agent_config.name, account_id, region)

            # Update the config with S3 URI
            agent_config.aws.s3_path = f"s3://{bucket_name}"
            agent_config.aws.s3_auto_create = False

            # Update the project config and save
            project_config.agents[agent_config.name] = agent_config
            save_config(project_config, config_path)

            log.info("S3 bucket available: %s", agent_config.aws.s3_path)

        # Step 5b: Upload to S3
        log.info("Uploading deployment package to S3...")
        step_start = time.time()
        if agent_config.aws.s3_path:
            # Parse S3 URI or path to get bucket and prefix
            s3_input = agent_config.aws.s3_path

            # Handle both s3://bucket/path and bucket/path formats
            if s3_input.startswith("s3://"):
                s3_path = s3_input[5:]  # Remove 's3://'
            else:
                s3_path = s3_input  # Use as-is

            if "/" in s3_path:
                bucket_name, prefix = s3_path.split("/", 1)
                s3_key = f"{prefix}/{agent_config.name}/deployment.zip"
            else:
                bucket_name = s3_path
                s3_key = f"{agent_config.name}/deployment.zip"

            # Use configured bucket
            s3 = session.client("s3")
            log.info("Uploading to s3://%s/%s...", bucket_name, s3_key)
            s3.upload_file(str(deployment_zip), bucket_name, s3_key, ExtraArgs={"ExpectedBucketOwner": account_id})
            s3_location = f"s3://{bucket_name}/{s3_key}"
        else:
            # Fallback to existing logic
            s3_location = packager.upload_to_s3(
                deployment_zip=deployment_zip,
                agent_name=agent_config.name,
                session=session,
                account_id=account_id,
            )
            # Extract bucket_name and s3_key from s3_location for later use
            if s3_location.startswith("s3://"):
                s3_path = s3_location[5:]  # Remove 's3://'
                if "/" in s3_path:
                    bucket_name, s3_key = s3_path.split("/", 1)
                else:
                    bucket_name = s3_path
                    s3_key = f"{agent_config.name}/deployment.zip"
        log.info("✓ Deployment package uploaded: %s", s3_location)

        # Step 6: Deploy to Runtime
        step_start = time.time()
        log.info("Deploying to Bedrock AgentCore Runtime...")

        bedrock_agentcore_client = BedrockAgentCoreClient(region)

        # Prepare environment variables
        if env_vars is None:
            env_vars = {}
        if agent_config.memory and agent_config.memory.memory_id:
            env_vars["BEDROCK_AGENTCORE_MEMORY_ID"] = agent_config.memory.memory_id
            env_vars["BEDROCK_AGENTCORE_MEMORY_NAME"] = agent_config.memory.memory_name

        # Build entrypoint array with optional OpenTelemetry instrumentation
        entrypoint_array = build_entrypoint_array(
            entrypoint_path, has_otel_distro, agent_config.aws.observability.enabled
        )
        if len(entrypoint_array) > 1:
            log.info("OpenTelemetry instrumentation enabled (aws-opentelemetry-distro detected)")

        # Create/update agent with code configuration
        agent_info = bedrock_agentcore_client.create_or_update_agent(
            agent_id=agent_config.bedrock_agentcore.agent_id,
            agent_name=agent_config.name,
            execution_role_arn=agent_config.aws.execution_role,
            deployment_type="direct_code_deploy",
            code_s3_bucket=bucket_name,
            code_s3_key=s3_key,
            runtime_type=agent_config.runtime_type,  # Optional
            entrypoint_array=entrypoint_array,  # Array format for Runtime API
            entrypoint_handler=None,  # Not used
            network_config=agent_config.aws.network_configuration.to_aws_dict(),
            authorizer_config=agent_config.get_authorizer_configuration(),
            request_header_config=agent_config.request_header_configuration,
            protocol_config=agent_config.aws.protocol_configuration.to_aws_dict(),
            env_vars=env_vars,
            auto_update_on_conflict=auto_update_on_conflict,
        )

        # Save deployment info
        agent_config.bedrock_agentcore.agent_id = agent_info["id"]
        agent_config.bedrock_agentcore.agent_arn = agent_info["arn"]

        # Reset session id if present
        existing_session_id = agent_config.bedrock_agentcore.agent_session_id
        if existing_session_id is not None:
            log.warning(
                "⚠️ Session ID will be reset to connect to the updated agent. "
                "The previous agent remains accessible via the original session ID: %s",
                existing_session_id,
            )
            agent_config.bedrock_agentcore.agent_session_id = None

        project_config.agents[agent_config.name] = agent_config
        save_config(project_config, config_path)

        log.info("✅ Agent created/updated: %s", agent_info["arn"])

        # Step 7: Wait for ready
        step_start = time.time()
        log.info("Waiting for agent endpoint to be ready...")
        bedrock_agentcore_client.wait_for_agent_endpoint_ready(agent_info["id"])

        # Step 8: Enable observability
        step_start = time.time()
        if agent_config.aws.observability.enabled:
            log.info("Enabling observability...")
            enable_transaction_search_if_needed(region, account_id)
            console_url = get_genai_observability_url(region)
            log.info("🔍 GenAI Observability Dashboard: %s", console_url)

        log.info("✅ Deployment completed successfully - Agent: %s", agent_info["arn"])

        return LaunchResult(
            mode="direct_code_deploy",
            agent_arn=agent_info["arn"],
            agent_id=agent_info["id"],
            s3_location=s3_location,
        )

    finally:
        # Cleanup temp deployment.zip (only if it was created)
        import shutil

        if "deployment_zip" in locals():
            shutil.rmtree(deployment_zip.parent, ignore_errors=True)
