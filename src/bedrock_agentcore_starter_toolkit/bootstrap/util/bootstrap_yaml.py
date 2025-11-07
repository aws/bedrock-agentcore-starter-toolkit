from pathlib import Path
from ..types import ProjectContext
import yaml

def write_minimal_bootstrap_project_yaml(ctx: ProjectContext) -> Path:
    file_path = ctx.output_dir / ".bedrock_agentcore.yaml"
    agent_name = ctx.agent_name

    data = {
        "default_agent": agent_name,
        "is_agentcore_bootstrap_project": True,
        "agents": {
            agent_name: {
                "name": agent_name,
                "entrypoint": str(ctx.src_dir),
                "deployment_type": ctx.deployment_type,
                 "aws": {
                    "region": None
                },
                "bedrock_agentcore": {
                    "agent_id": None,
                    "agent_arn": None,
                    "agent_session_id": None,
                }
            }
        },
    }

    with file_path.open("w") as f:
        yaml.safe_dump(data, f, sort_keys=False)

    return file_path