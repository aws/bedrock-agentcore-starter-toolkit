from pathlib import Path

import yaml
from ...services.ecr import get_region
from ...services.runtime import BedrockAgentCoreClient, generate_session_id
from .config import load_config, save_config

def resolve_bootstrap_project_yaml():
    """
    Bootstrap command can't populate the runtime id/arn because it's not known until the service is deployed
    This command uses a workaround to find the correct id by searching for the agent name as the prefix
    Only the default_agent is supported by this command. Not multi agent
    """
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"
    bootstrap_project = load_config(config_path)
    default_agent = bootstrap_project.default_agent
    default_agent_config = bootstrap_project.agents[default_agent]
    if not bootstrap_project.is_agentcore_bootstrap_project:
        return # do nothing
    
    region = get_region()
    default_agent_config.aws.region = region
    default_runtime_config = default_agent_config.bedrock_agentcore

    runtimeId = default_runtime_config.agent_id
    runtimeArn = default_runtime_config.agent_arn
    if not (runtimeId and runtimeArn):
        # find the agent based on name, count matches for conflict edge case
        match_count = 0
        client = BedrockAgentCoreClient(region=region) 
        for agent in client.list_agents():
            if agent["agentRuntimeName"] == default_agent:
                runtimeId = agent["agentRuntimeId"]
                runtimeArn = agent["agentRuntimeArn"]
                match_count += 1
                break
        if match_count == 0:
            raise Exception(f"Could not find an agentcore runtime resource with name {default_agent}")
        if match_count > 1:
            raise Exception(f"Found multiple agents with the same name. Manually update the .bedrock_agentcore.yaml to specify an agent")

    default_runtime_config.agent_arn = runtimeArn
    default_runtime_config.agent_id = runtimeId
    default_runtime_config.agent_session_id = generate_session_id()
    save_config(bootstrap_project, config_path)
    

