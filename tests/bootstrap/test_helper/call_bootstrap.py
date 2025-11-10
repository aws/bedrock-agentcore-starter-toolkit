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


FIXTURES = Path(__file__).parent.parent / "fixtures" / "bedrock_agentcore_config"
test_runner = CliRunner()

# ---------------------------------------------------------------------------
# All tests (cdk and terraform) use this setup
# Since only the IAC varies by scenario input, we only need to exercise each SDK at least once
# ---------------------------------------------------------------------------
SCENARIO_TO_SDK = {
    "scenario_0": SDKProvider.STRANDS, # custom auth, stm and ltm, custom headers
    # "scenario_1": SDKProvider.OPENAI,
    # "scenario_2": SDKProvider.CLAUDE,
}

def run_bootstrap(tmp_path, monkeypatch, scenario, iac):
    """Runs the CLI generator and returns the project directory."""
    sdk = SCENARIO_TO_SDK[scenario]

    # Put the fixture into the working directory.
    shutil.copy(FIXTURES / f"{scenario}.yaml", tmp_path / ".bedrock_agentcore.yaml")
    monkeypatch.chdir(tmp_path)

    project_name = "testProj"

    result = test_runner.invoke(
        bootstrap_app,
        [
            "--project-name", project_name,
            "--iac", iac,
            "--sdk", sdk,
        ],
    )
    assert result.exit_code == 0, result.stdout

    return tmp_path / project_name, sdk

