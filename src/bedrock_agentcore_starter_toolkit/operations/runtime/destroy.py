"""Destroy operation - removes Bedrock AgentCore resources from AWS."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from ...services.runtime import BedrockAgentCoreClient
from ...utils.runtime.config import load_config, save_config
from ...utils.runtime.schema import BedrockAgentCoreAgentSchema, BedrockAgentCoreConfigSchema
from .models import DestroyResult

log = logging.getLogger(__name__)


def destroy_bedrock_agentcore(
    config_path: Path,
    agent_name: Optional[str] = None,
    dry_run: bool = False,
    force: bool = False,
    delete_ecr_repo: bool = False,
) -> DestroyResult:
    """Destroy Bedrock AgentCore resources.

    Args:
        config_path: Path to the configuration file
        agent_name: Name of the agent to destroy (default: use default agent)
        dry_run: If True, only show what would be destroyed without actually doing it
        force: If True, skip confirmation prompts
        delete_ecr_repo: If True, also delete the ECR repository after removing images

    Returns:
        DestroyResult: Details of what was destroyed or would be destroyed

    Raises:
        FileNotFoundError: If configuration file doesn't exist
        ValueError: If agent is not found or not deployed
        RuntimeError: If destruction fails
    """
    log.info("Starting destroy operation for agent: %s (dry_run=%s, delete_ecr_repo=%s)", 
             agent_name or "default", dry_run, delete_ecr_repo)

    try:
        # Load configuration
        project_config = load_config(config_path)
        agent_config = project_config.get_agent_config(agent_name)
        
        if not agent_config:
            raise ValueError(f"Agent '{agent_name or 'default'}' not found in configuration")

        # Initialize result
        result = DestroyResult(agent_name=agent_config.name, dry_run=dry_run)

        # Check if agent is deployed
        if not agent_config.bedrock_agentcore:
            result.warnings.append("Agent is not deployed, nothing to destroy")
            return result

        # Initialize AWS session and clients
        session = boto3.Session(region_name=agent_config.aws.region)
        
        # 1. Destroy Bedrock AgentCore endpoint (if exists)
        _destroy_agentcore_endpoint(session, agent_config, result, dry_run)
        
        # 2. Destroy Bedrock AgentCore agent
        _destroy_agentcore_agent(session, agent_config, result, dry_run)
        
        # 3. Remove ECR images and optionally the repository
        _destroy_ecr_images(session, agent_config, result, dry_run, delete_ecr_repo)
        
        # 4. Remove CodeBuild project
        _destroy_codebuild_project(session, agent_config, result, dry_run)
        
        # 5. Remove IAM execution role (if not used by other agents)
        _destroy_iam_role(session, project_config, agent_config, result, dry_run)
        
        # 6. Clean up configuration
        if not dry_run and not result.errors:
            _cleanup_agent_config(config_path, project_config, agent_config.name, result)

        log.info("Destroy operation completed. Resources removed: %d, Warnings: %d, Errors: %d",
                len(result.resources_removed), len(result.warnings), len(result.errors))
        
        return result

    except Exception as e:
        log.error("Destroy operation failed: %s", str(e))
        raise RuntimeError(f"Destroy operation failed: {e}") from e


def _destroy_agentcore_endpoint(
    session: boto3.Session,
    agent_config: BedrockAgentCoreAgentSchema,
    result: DestroyResult,
    dry_run: bool,
) -> None:
    """Destroy Bedrock AgentCore endpoint."""
    if not agent_config.bedrock_agentcore:
        return

    try:
        client = BedrockAgentCoreClient(agent_config.aws.region)
        
        # Get agent details to find endpoint
        agent_id = agent_config.bedrock_agentcore.agent_id
        if not agent_id:
            result.warnings.append("No agent ID found, skipping endpoint destruction")
            return

        if dry_run:
            result.resources_removed.append(f"AgentCore endpoint for agent {agent_id} (DRY RUN)")
            return

        # Try to get and delete endpoint
        try:
            endpoint_response = client.get_agent_runtime_endpoint(agent_id)
            endpoint_arn = endpoint_response.get("agentRuntimeEndpointArn")
            if endpoint_arn:
                # Note: There's no direct delete endpoint method in the current client
                # This would need to be implemented if endpoint deletion is supported
                result.warnings.append(f"Endpoint deletion not implemented yet: {endpoint_arn}")
                log.warning("Endpoint deletion not implemented yet: %s", endpoint_arn)
            else:
                result.warnings.append("No endpoint found for agent")
        except ClientError as e:
            if e.response["Error"]["Code"] not in ["ResourceNotFoundException", "NotFound"]:
                result.warnings.append(f"Failed to get endpoint info: {e}")
                log.warning("Failed to get endpoint info: %s", e)
            else:
                result.warnings.append("Endpoint not found or already deleted")

    except Exception as e:
        result.warnings.append(f"Error during endpoint destruction: {e}")
        log.warning("Error during endpoint destruction: %s", e)


def _destroy_agentcore_agent(
    session: boto3.Session,
    agent_config: BedrockAgentCoreAgentSchema,
    result: DestroyResult,
    dry_run: bool,
) -> None:
    """Destroy Bedrock AgentCore agent."""
    if not agent_config.bedrock_agentcore or not agent_config.bedrock_agentcore.agent_arn:
        result.warnings.append("No agent ARN found, skipping agent destruction")
        return

    try:
        client = BedrockAgentCoreClient(agent_config.aws.region)
        agent_arn = agent_config.bedrock_agentcore.agent_arn
        agent_id = agent_config.bedrock_agentcore.agent_id

        if dry_run:
            result.resources_removed.append(f"AgentCore agent: {agent_arn} (DRY RUN)")
            return

        # Delete the agent
        try:
            # Use the control plane client directly since there's no delete_agent_runtime method
            # in the BedrockAgentCoreClient class
            control_client = session.client("bedrock-agentcore-control", region_name=agent_config.aws.region)
            control_client.delete_agent_runtime(agentRuntimeId=agent_id)
            result.resources_removed.append(f"AgentCore agent: {agent_arn}")
            log.info("Deleted AgentCore agent: %s", agent_arn)
        except ClientError as e:
            if e.response["Error"]["Code"] not in ["ResourceNotFoundException", "NotFound"]:
                result.errors.append(f"Failed to delete agent {agent_arn}: {e}")
                log.error("Failed to delete agent: %s", e)
            else:
                result.warnings.append(f"Agent {agent_arn} not found (may have been deleted already)")

    except Exception as e:
        result.errors.append(f"Error during agent destruction: {e}")
        log.error("Error during agent destruction: %s", e)


def _destroy_ecr_images(
    session: boto3.Session,
    agent_config: BedrockAgentCoreAgentSchema,
    result: DestroyResult,
    dry_run: bool,
    delete_ecr_repo: bool = False,
) -> None:
    """Remove ECR images and optionally the repository for this specific agent."""
    if not agent_config.aws.ecr_repository:
        result.warnings.append("No ECR repository configured, skipping image cleanup")
        return

    try:
        # Create ECR client with explicit region specification
        ecr_client = session.client("ecr", region_name=agent_config.aws.region)
        ecr_uri = agent_config.aws.ecr_repository
        
        # Extract repository name from URI
        # Format: account.dkr.ecr.region.amazonaws.com/repo-name
        repo_name = ecr_uri.split("/")[-1]
        
        log.info("Checking ECR repository: %s in region: %s", repo_name, agent_config.aws.region)

        try:
            # List all images in the repository (both tagged and untagged)
            response = ecr_client.list_images(repositoryName=repo_name)
            log.debug("ECR list_images response: %s", response)
            
            # Fix: use correct response key 'imageIds' instead of 'imageDetails'
            all_images = response.get("imageIds", [])
            if not all_images:
                if delete_ecr_repo:
                    # Repository exists but is empty, we can delete it
                    if dry_run:
                        result.resources_removed.append(f"ECR repository: {repo_name} (empty, DRY RUN)")
                    else:
                        _delete_ecr_repository(ecr_client, repo_name, result)
                else:
                    result.warnings.append(f"No images found in ECR repository: {repo_name}")
                return

            if dry_run:
                # Fix: imageIds structure has imageTag (string) not imageTags (array)  
                tagged_count = len([img for img in all_images if img.get("imageTag")])
                untagged_count = len([img for img in all_images if not img.get("imageTag")])
                result.resources_removed.append(
                    f"ECR images in repository {repo_name}: {tagged_count} tagged, {untagged_count} untagged (DRY RUN)"
                )
                if delete_ecr_repo:
                    result.resources_removed.append(f"ECR repository: {repo_name} (DRY RUN)")
                return

            # Prepare images for deletion - imageIds are already in the correct format
            images_to_delete = []
            
            for image in all_images:
                # imageIds structure already contains the correct identifiers
                image_id = {}
                
                # If image has a tag, use it
                if image.get("imageTag"):
                    image_id["imageTag"] = image["imageTag"]
                # If no tag, use image digest  
                elif image.get("imageDigest"):
                    image_id["imageDigest"] = image["imageDigest"]
                
                if image_id:
                    images_to_delete.append(image_id)

            if images_to_delete:
                # Delete images in batches (ECR has a limit of 100 images per batch)
                batch_size = 100
                total_deleted = 0
                
                for i in range(0, len(images_to_delete), batch_size):
                    batch = images_to_delete[i:i + batch_size]
                    
                    delete_response = ecr_client.batch_delete_image(
                        repositoryName=repo_name,
                        imageIds=batch
                    )
                    
                    deleted_images = delete_response.get("imageIds", [])
                    total_deleted += len(deleted_images)
                    
                    # Log any failures in this batch
                    failures = delete_response.get("failures", [])
                    for failure in failures:
                        log.warning("Failed to delete image: %s - %s", 
                                  failure.get("imageId"), failure.get("failureReason"))

                result.resources_removed.append(f"ECR images: {total_deleted} images from {repo_name}")
                log.info("Deleted %d ECR images from %s", total_deleted, repo_name)
                
                # Log any partial failures
                if total_deleted < len(images_to_delete):
                    failed_count = len(images_to_delete) - total_deleted
                    result.warnings.append(
                        f"Some ECR images could not be deleted: {failed_count} out of {len(images_to_delete)} failed"
                    )
                
                # Delete the repository if requested and all images were deleted successfully
                if delete_ecr_repo and total_deleted == len(images_to_delete):
                    _delete_ecr_repository(ecr_client, repo_name, result)
                elif delete_ecr_repo and total_deleted < len(images_to_delete):
                    result.warnings.append(f"Cannot delete ECR repository {repo_name}: some images failed to delete")
            else:
                result.warnings.append(f"No valid image identifiers found in {repo_name}")

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "RepositoryNotFoundException":
                result.warnings.append(f"ECR repository {repo_name} not found")
            elif error_code == "RepositoryNotEmptyException":
                result.warnings.append(f"ECR repository {repo_name} could not be deleted (not empty)")
            else:
                result.warnings.append(f"Failed to delete ECR images: {e}")
                log.warning("Failed to delete ECR images: %s", e)

    except Exception as e:
        result.warnings.append(f"Error during ECR cleanup: {e}")
        log.warning("Error during ECR cleanup: %s", e)


def _delete_ecr_repository(ecr_client, repo_name: str, result: DestroyResult) -> None:
    """Delete an ECR repository after ensuring it's empty."""
    try:
        # Verify repository is empty before deletion
        response = ecr_client.list_images(repositoryName=repo_name)
        remaining_images = response.get("imageIds", [])
        
        if remaining_images:
            result.warnings.append(f"Cannot delete ECR repository {repo_name}: repository is not empty")
            return
        
        # Delete the empty repository
        ecr_client.delete_repository(repositoryName=repo_name)
        result.resources_removed.append(f"ECR repository: {repo_name}")
        log.info("Deleted ECR repository: %s", repo_name)
        
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "RepositoryNotFoundException":
            result.warnings.append(f"ECR repository {repo_name} not found (may have been deleted already)")
        elif error_code == "RepositoryNotEmptyException":
            result.warnings.append(f"Cannot delete ECR repository {repo_name}: repository is not empty")
        else:
            result.warnings.append(f"Failed to delete ECR repository {repo_name}: {e}")
            log.warning("Failed to delete ECR repository: %s", e)
    except Exception as e:
        result.warnings.append(f"Error deleting ECR repository {repo_name}: {e}")
        log.warning("Error deleting ECR repository: %s", e)


def _destroy_codebuild_project(
    session: boto3.Session,
    agent_config: BedrockAgentCoreAgentSchema,
    result: DestroyResult,
    dry_run: bool,
) -> None:
    """Remove CodeBuild project for this agent."""
    try:
        codebuild_client = session.client("codebuild", region_name=agent_config.aws.region)
        project_name = f"bedrock-agentcore-{agent_config.name}-builder"

        if dry_run:
            result.resources_removed.append(f"CodeBuild project: {project_name} (DRY RUN)")
            return

        try:
            codebuild_client.delete_project(name=project_name)
            result.resources_removed.append(f"CodeBuild project: {project_name}")
            log.info("Deleted CodeBuild project: %s", project_name)
        except ClientError as e:
            if e.response["Error"]["Code"] not in ["ResourceNotFoundException"]:
                result.warnings.append(f"Failed to delete CodeBuild project {project_name}: {e}")
                log.warning("Failed to delete CodeBuild project: %s", e)
            else:
                result.warnings.append(f"CodeBuild project {project_name} not found")

    except Exception as e:
        result.warnings.append(f"Error during CodeBuild cleanup: {e}")
        log.warning("Error during CodeBuild cleanup: %s", e)


def _destroy_iam_role(
    session: boto3.Session,
    project_config: BedrockAgentCoreConfigSchema,
    agent_config: BedrockAgentCoreAgentSchema,
    result: DestroyResult,
    dry_run: bool,
) -> None:
    """Remove IAM execution role only if not used by other agents."""
    if not agent_config.aws.execution_role:
        result.warnings.append("No execution role configured, skipping IAM cleanup")
        return

    try:
        # Note: IAM is a global service, but we specify region for consistency
        iam_client = session.client("iam", region_name=agent_config.aws.region)
        role_arn = agent_config.aws.execution_role
        role_name = role_arn.split("/")[-1]

        # Check if other agents use the same role
        other_agents_using_role = [
            name for name, agent in project_config.agents.items()
            if name != agent_config.name and agent.aws.execution_role == role_arn
        ]

        if other_agents_using_role:
            result.warnings.append(
                f"IAM role {role_name} is used by other agents: {other_agents_using_role}. Not deleting."
            )
            return

        if dry_run:
            result.resources_removed.append(f"IAM execution role: {role_name} (DRY RUN)")
            return

        try:
            # Delete attached policies first
            try:
                policies = iam_client.list_attached_role_policies(RoleName=role_name)
                for policy in policies.get("AttachedPolicies", []):
                    iam_client.detach_role_policy(
                        RoleName=role_name,
                        PolicyArn=policy["PolicyArn"]
                    )
            except ClientError:
                pass  # Continue if policy detachment fails

            # Delete inline policies
            try:
                inline_policies = iam_client.list_role_policies(RoleName=role_name)
                for policy_name in inline_policies.get("PolicyNames", []):
                    iam_client.delete_role_policy(RoleName=role_name, PolicyName=policy_name)
            except ClientError:
                pass  # Continue if inline policy deletion fails

            # Delete the role
            iam_client.delete_role(RoleName=role_name)
            result.resources_removed.append(f"IAM execution role: {role_name}")
            log.info("Deleted IAM role: %s", role_name)

        except ClientError as e:
            if e.response["Error"]["Code"] not in ["NoSuchEntity"]:
                result.warnings.append(f"Failed to delete IAM role {role_name}: {e}")
                log.warning("Failed to delete IAM role: %s", e)
            else:
                result.warnings.append(f"IAM role {role_name} not found")

    except Exception as e:
        result.warnings.append(f"Error during IAM cleanup: {e}")
        log.warning("Error during IAM cleanup: %s", e)


def _cleanup_agent_config(
    config_path: Path,
    project_config: BedrockAgentCoreConfigSchema,
    agent_name: str,
    result: DestroyResult,
) -> None:
    """Remove agent configuration from the config file."""
    try:
        # Clear the bedrock_agentcore deployment info but keep the agent config
        if agent_name in project_config.agents:
            agent_config = project_config.agents[agent_name]
            agent_config.bedrock_agentcore = None
            
            # Save updated configuration
            save_config(project_config, config_path)
            result.resources_removed.append(f"Agent deployment configuration: {agent_name}")
            log.info("Cleared deployment configuration for agent: %s", agent_name)
        else:
            result.warnings.append(f"Agent {agent_name} not found in configuration")

    except Exception as e:
        result.warnings.append(f"Failed to update configuration: {e}")
        log.warning("Failed to update configuration: %s", e)