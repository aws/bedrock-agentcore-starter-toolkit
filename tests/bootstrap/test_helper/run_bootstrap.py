import shutil
from pathlib import Path
from typer.testing import CliRunner

from bedrock_agentcore_starter_toolkit.bootstrap.constants import (
    SDKProvider
)
from bedrock_agentcore_starter_toolkit.cli.bootstrap.commands import (
    bootstrap_app,
)
from .syrupy_util import snapshot_dir_tree
from unittest.mock import patch

FIXTURES = Path(__file__).parent.parent / "fixtures"
CONFIG_FIXTURES = FIXTURES / "bedrock_agentcore_config"
SRC_FIXTURES = FIXTURES / "src_provided"
test_runner = CliRunner()

# ---------------------------------------------------------------------------
# Both cdk and terraform tests use this setup
# Since only the IAC varies by scenario input, we only need to exercise each SDK at least once
# ---------------------------------------------------------------------------
SCENARIO_TO_SDK = {
    "scenario_0": SDKProvider.STRANDS, # custom auth, stm and ltm, custom headers
    "scenario_1": SDKProvider.OPENAI_AGENTS, # default settings: stm
    "scenario_2": None, # Source is provided so there is no sdk provider
}

SCENARIO_WITH_SRC_PROVIDED = set(["scenario_2"])

def run_bootstrap(tmp_path, monkeypatch, scenario, iac):
    """Runs the CLI generator and returns the project directory."""
    sdk = SCENARIO_TO_SDK[scenario]

    # Put the fixture into the working directory.
    if scenario in SCENARIO_WITH_SRC_PROVIDED:
        shutil.copytree(SRC_FIXTURES / scenario, tmp_path, dirs_exist_ok=True)
    else:
        shutil.copy(CONFIG_FIXTURES / f"{scenario}.yaml", tmp_path / ".bedrock_agentcore.yaml")
    monkeypatch.chdir(tmp_path)

    project_name = "testProj"

    # patch confirm copy source prompt to yes
    with patch(
        "bedrock_agentcore_starter_toolkit.cli.bootstrap.prompt_util.prompt",
        return_value="y"
    ):
        result = test_runner.invoke(
            bootstrap_app,
            [
                "--project-name", project_name,
                "--iac", iac,
                "--sdk", sdk,
            ],
            catch_exceptions=False,
        )

    if result.exit_code != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    assert result.exit_code == 0

    return tmp_path / project_name, sdk

