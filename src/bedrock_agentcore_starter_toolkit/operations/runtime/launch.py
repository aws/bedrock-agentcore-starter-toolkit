"""Launch operation - deploys Bedrock AgentCore locally or to cloud."""

import json
import logging
import time
import urllib.parse
from pathlib import Path
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from ...services.codebuild import CodeBuildService
from ...services.ecr import deploy_to_ecr, get_or_create_ecr_repository
from ...services.runtime import BedrockAgentCoreClient
from ...utils.runtime.config import load_config, save_config
from ...utils.runtime.container import ContainerRuntime
from ...utils.runtime.schema import BedrockAgentCoreAgentSchema, BedrockAgentCoreConfigSchema
from .create_role import get_or_create_runtime_execution_role
from .models import LaunchResult

log = logging.getLogger(__name__)


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

        log.info("✅ ECR repository available: %s", ecr_uri)
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

        log.info("✅ Execution role available: %s", execution_role_arn)
        return execution_role_arn

    # Step 4: No role and auto-create disabled
    raise ValueError("Execution role not configured and auto-create not enabled")


def _deploy_to_bedrock_agentcore(
    agent_config: BedrockAgentCoreAgentSchema,
    project_config: BedrockAgentCoreConfigSchema,
    config_path: Path,
    agent_name: str,
    ecr_uri: str,
    region: str,
    env_vars: Optional[dict] = None,
    auto_update_on_conflict: bool = False,
):
    """Deploy agent to Bedrock AgentCore with retry logic for role validation."""
    log.info("Deploying to Bedrock AgentCore...")

    bedrock_agentcore_client = BedrockAgentCoreClient(region)

    # Transform network configuration to AWS API format
    network_config = agent_config.aws.network_configuration.to_aws_dict()
    protocol_config = agent_config.aws.protocol_configuration.to_aws_dict()

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
                image_uri=f"{ecr_uri}:latest",
                execution_role_arn=agent_config.aws.execution_role,
                network_config=network_config,
                authorizer_config=agent_config.get_authorizer_configuration(),
                protocol_config=protocol_config,
                env_vars=env_vars,
                auto_update_on_conflict=auto_update_on_conflict,
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

    log.info("✅ Agent created/updated: %s", agent_arn)

    # Wait for agent to be ready
    log.info("Polling for endpoint to be ready...")
    result = bedrock_agentcore_client.wait_for_agent_endpoint_ready(agent_id)
    log.info("Agent endpoint: %s", result)

    return agent_id, agent_arn


def launch_bedrock_agentcore(
    config_path: Path,
    agent_name: Optional[str] = None,
    local: bool = False,
    use_codebuild: bool = True,
    env_vars: Optional[dict] = None,
    auto_update_on_conflict: bool = False,
) -> LaunchResult:
    """Launch Bedrock AgentCore locally or to cloud.

    Args:
        config_path: Path to BedrockAgentCore configuration file
        agent_name: Name of agent to launch (for project configurations)
        local: Whether to run locally
        use_codebuild: Whether to use CodeBuild for ARM64 builds
        env_vars: Environment variables to pass to local container (dict of key-value pairs)
        auto_update_on_conflict: Whether to automatically update when agent already exists (default: False)

    Returns:
        LaunchResult model with launch details
    """
    # Load project configuration
    project_config = load_config(config_path)
    agent_config = project_config.get_agent_config(agent_name)

    # Handle CodeBuild deployment (but not for local mode)
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

    # Get build context - always use project root (where config and Dockerfile are)
    build_dir = config_path.parent

    bedrock_agentcore_name = agent_config.name
    tag = f"bedrock_agentcore-{bedrock_agentcore_name}:latest"

    # Step 1: Build Docker image (only if we need it)
    success, output = runtime.build(build_dir, tag)
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
    ecr_repository_arn = f"arn:aws:ecr:{region}:{account_id}:repository/{ecr_uri.split('/')[-1]}"

    # Setup execution role only if not ECR-only mode
    if not ecr_only:
        _ensure_execution_role(agent_config, project_config, config_path, agent_name, region, account_id)

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

    source_location = codebuild_service.upload_source(agent_name=agent_name)

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
        log.info("✅ CodeBuild project configuration saved")
    else:
        log.info("✅ ECR-only build completed (project configuration not saved)")

    return build_id, ecr_uri, region, account_id


def _launch_with_codebuild(
    config_path: Path,
    agent_name: str,
    agent_config,
    project_config,
    auto_update_on_conflict: bool = False,
    env_vars: Optional[dict] = None,
) -> LaunchResult:
    """Launch using CodeBuild for ARM64 builds."""
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
