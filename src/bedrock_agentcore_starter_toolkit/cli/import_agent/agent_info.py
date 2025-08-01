"""This module provides utility functions to interact with AWS Bedrock Agent services."""

import json
import os

import boto3
from prance import ResolvingParser
from ruamel.yaml import YAML  # pylint: disable=import-error # type: ignore

from ...services.import_agent.utils import clean_variable_name, fix_field


def get_clients(credentials, region_name="us-west-2"):
    """Get Bedrock and Bedrock Agent clients using the provided credentials and region.

    Args:
        credentials: AWS credentials
        region_name: AWS region name (default: us-west-2)

    Returns:
        tuple: (bedrock_client, bedrock_agent_client)
    """
    boto3_session = boto3.Session(
        aws_access_key_id=credentials.access_key,
        aws_secret_access_key=credentials.secret_key,
        aws_session_token=credentials.token,
        region_name=region_name,
    )

    bedrock_agent_client = boto3_session.client("bedrock-agent", region_name=region_name)
    bedrock_client = boto3_session.client("bedrock", region_name=region_name)

    return bedrock_client, bedrock_agent_client


def get_agents(bedrock_agent_client) -> list[dict[str, str]]:
    """Retrieve a list of agents in the AWS account.

    Args:
        bedrock_client: The Bedrock client.
        bedrock_agent_client: The Bedrock Agent client.

    Returns:
        list: A list of dictionaries containing agent information.
    """
    agents_in_account = bedrock_agent_client.list_agents(maxResults=200)["agentSummaries"]
    return [
        {
            "id": agent.get("agentId", ""),
            "name": agent.get("agentName", ""),
            "description": agent.get("description", ""),
        }
        for agent in agents_in_account
    ]


def get_agent_aliases(bedrock_agent_client, agent_id):
    """Retrieve a list of aliases for a specific agent.

    Args:
        bedrock_client: The Bedrock client.
        bedrock_agent_client: The Bedrock Agent client.
        agent_id (str): The ID of the agent.

    Returns:
        list: A list of dictionaries containing alias information for the specified agent.
    """
    aliases_for_agent = bedrock_agent_client.list_agent_aliases(agentId=agent_id)["agentAliasSummaries"]
    return [
        {
            "id": agent.get("agentAliasId", ""),
            "name": agent.get("agentAliasName", ""),
            "description": agent.get("description", ""),
        }
        for agent in aliases_for_agent
    ]


def get_agent_info(agent_id: str, agent_alias_id: str, bedrock_client, bedrock_agent_client):
    """Retrieve detailed information about a specific agent and its alias.

    Args:
        agent_id (str): The ID of the agent.
        agent_alias_id (str): The ID of the agent alias.
        bedrock_client: The Bedrock client.
        bedrock_agent_client: The Bedrock Agent client.

    Returns:
        dict: A dictionary containing detailed information about the agent, its alias, action groups,
        knowledge bases, and collaborators.
    """
    agent_version = bedrock_agent_client.get_agent_alias(agentId=agent_id, agentAliasId=agent_alias_id)["agentAlias"][
        "routingConfiguration"
    ][0]["agentVersion"]

    identifier = agent_id
    version = agent_version

    targets = {}

    agentinfo = bedrock_agent_client.get_agent(agentId=identifier)["agent"]

    # reduce agent prompt configurations to only the enabled set
    if agentinfo["orchestrationType"] == "DEFAULT":
        agentinfo["promptOverrideConfiguration"]["promptConfigurations"] = [
            fix_field(config, "basePromptTemplate")
            for config in agentinfo["promptOverrideConfiguration"]["promptConfigurations"]
            if config["promptState"] == "ENABLED"
        ]

    # get agent guardrail information
    guardrail_config = agentinfo.get("guardrailConfiguration", {})
    guardrail_identifier = guardrail_config.get("guardrailIdentifier")
    guardrail_version = guardrail_config.get("guardrailVersion")
    if guardrail_identifier and guardrail_version:
        agentinfo["guardrailConfiguration"] = bedrock_client.get_guardrail(
            guardrailIdentifier=guardrail_identifier,
            guardrailVersion=guardrail_version,
        )
        agentinfo["guardrailConfiguration"].pop("ResponseMetadata")

    # get more model information
    model_inference_profile = agentinfo["foundationModel"].split("/")[-1]
    model_id = ".".join(model_inference_profile.split(".")[-2:])
    agentinfo["model"] = bedrock_client.get_foundation_model(modelIdentifier=model_id)["modelDetails"]
    agentinfo["alias"] = agent_alias_id

    # get agent action groups and lambdas in them
    action_groups = bedrock_agent_client.list_agent_action_groups(agentId=identifier, agentVersion=version)[
        "actionGroupSummaries"
    ]
    for action_group in action_groups:
        action_group_info = bedrock_agent_client.get_agent_action_group(
            agentId=identifier,
            agentVersion=version,
            actionGroupId=action_group["actionGroupId"],
        )["agentActionGroup"]
        action_group.update(action_group_info)
        action_group["actionGroupName"] = clean_variable_name(action_group["actionGroupName"])

        if action_group.get("apiSchema", False):
            open_api_schema = action_group["apiSchema"].get("payload", False)
            if open_api_schema:
                yaml = YAML(typ="safe")
                action_group["apiSchema"]["payload"] = yaml.load(open_api_schema)
            else:
                s3_bucket_name = action_group["apiSchema"]["s3"]["s3BucketName"]
                s3_object_key = action_group["apiSchema"]["s3"]["s3ObjectKey"]

                s3_client = boto3.client("s3")
                response = s3_client.get_object(Bucket=s3_bucket_name, Key=s3_object_key)
                yaml_content = response["Body"].read().decode("utf-8")
                yaml = YAML(typ="safe")
                action_group["apiSchema"]["payload"] = yaml.load(yaml_content)
            # resolve the openapi schema references
            parser = ResolvingParser(spec_string=json.dumps(action_group["apiSchema"]["payload"]))
            action_group["apiSchema"]["payload"] = parser.specification

    # get agent knowledge bases
    knowledge_bases = bedrock_agent_client.list_agent_knowledge_bases(agentId=identifier, agentVersion=version)[
        "agentKnowledgeBaseSummaries"
    ]
    for knowledge_base in knowledge_bases:
        knowledge_base_info = bedrock_agent_client.get_knowledge_base(
            knowledgeBaseId=knowledge_base["knowledgeBaseId"],
        )["knowledgeBase"]
        knowledge_base_info["name"] = clean_variable_name(knowledge_base_info["name"])
        for key, value in knowledge_base_info.items():
            if key not in knowledge_base:
                knowledge_base[key] = value

    agentinfo["version"] = version
    targets.update(
        {
            "agent": agentinfo,
            "action_groups": action_groups,
            "knowledge_bases": knowledge_bases,
        }
    )

    # get agent collaborators and recursively fetch their information
    targets["collaborators"] = []
    if agentinfo.get("agentCollaboration", "DISABLED") != "DISABLED":
        collaborators = bedrock_agent_client.list_agent_collaborators(agentId=agent_id, agentVersion=agent_version)[
            "agentCollaboratorSummaries"
        ]

        for collaborator in collaborators:
            arn = collaborator["agentDescriptor"]["aliasArn"].split("/")
            collab_id = arn[1]
            collab_alias_id = arn[2]
            if collab_alias_id == agent_alias_id:
                continue
            collaborator_info = get_agent_info(collab_id, collab_alias_id, bedrock_client, bedrock_agent_client)
            collaborator_info["collaboratorName"] = clean_variable_name(collaborator["collaboratorName"])
            collaborator_info["collaborationInstruction"] = collaborator.get("collaborationInstruction", "")
            collaborator_info["relayConversationHistory"] = collaborator.get("relayConversationHistory", "DISABLED")

            targets["collaborators"].append(collaborator_info)

        if identifier == agent_id and version == agent_version and collaborators:
            agentinfo["isPrimaryAgent"] = True
            agentinfo["collaborators"] = collaborators

    return targets


def auth_and_get_info(agent_id: str, agent_alias_id: str, output_dir: str, region_name: str = "us-west-2"):
    """Authenticate with AWS and retrieve agent information.

    Args:
        agent_id (str): The ID of the agent.
        agent_alias_id (str): The ID of the agent alias.
        output_dir (str): The directory where the output Bedrock Agent configuration will be saved.
        region_name (str): AWS region name (default: us-west-2).

    Returns:
        dict: A dictionary containing detailed information about the agent, its alias,
        action groups, knowledge bases, and collaborators.
    """
    credentials = boto3.Session().get_credentials()
    bedrock_client, bedrock_agent_client = get_clients(credentials, region_name)
    output = get_agent_info(agent_id, agent_alias_id, bedrock_client, bedrock_agent_client)

    # Save the output Bedrock Agent configuration to a file for debugging and reference
    with open(os.path.join(output_dir, "bedrock_config.json"), "a+", encoding="utf-8") as f:
        f.truncate(0)
        json.dump(output, f, ensure_ascii=False, indent=4, default=str)

    return output
