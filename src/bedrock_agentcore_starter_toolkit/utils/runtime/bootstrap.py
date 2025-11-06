from pathlib import Path

from ...services.ecr import get_region
from ...services.runtime import BedrockAgentCoreClient, generate_session_id
from .config import load_config, save_config
from ...utils.runtime.schema import BedrockAgentCoreConfigSchema

def resolve_bootstrap_project_config() -> BedrockAgentCoreConfigSchema:
    """
    Handle the unset bootstrap config. Save a new one and return it.

    Bootstrap command can't populate the runtime id/arn because it's not known until the IAC is deployed
    This command uses a workaround to find the id/arn by iterating through the agentRuntimeName properties in a list_agents() call
    Only the default_agent is supported by this command. Not multi agent.
    """
    config_path = Path.cwd() / ".bedrock_agentcore.yaml"
    bootstrap_project = load_config(config_path)
    default_agent = bootstrap_project.default_agent
    default_agent_config = bootstrap_project.agents[default_agent]
    if not bootstrap_project.is_agentcore_bootstrap_project:
        return # no-op
    
    region = get_region()
    default_agent_config.aws.region = region
    default_runtime_config = default_agent_config.bedrock_agentcore

    runtimeId = default_runtime_config.agent_id
    runtimeArn = default_runtime_config.agent_arn
    if not (runtimeId and runtimeArn):
        # find the agent based on name, count matches for name-conflict edge case
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
            raise Exception(f"Found multiple agents with the same name: {default_agent}. Manually update the .bedrock_agentcore.yaml to specify an agent")

    # set new config vars
    default_runtime_config.agent_arn = runtimeArn
    default_runtime_config.agent_id = runtimeId
    default_runtime_config.agent_session_id = generate_session_id()
    
    # update the YAML with new values
    save_config(bootstrap_project, config_path)

    # return the updated schema object
    return load_config(config_path)
    

