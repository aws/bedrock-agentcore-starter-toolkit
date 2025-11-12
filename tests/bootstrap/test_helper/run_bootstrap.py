import shutil
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from bedrock_agentcore_starter_toolkit.cli.bootstrap.commands import (
    bootstrap_app,
)

from .bootstrap_scenarios import SCENARIOS, ScenarioConfig

FIXTURES = Path(__file__).parent.parent / "fixtures" / "scenarios"
test_runner = CliRunner()


def run_bootstrap(tmp_path, monkeypatch, scenario, iac) -> tuple[Path, ScenarioConfig]:
    """Runs the CLI generator and returns the project directory and the ScenarioConfig used"""
    scenario_config = SCENARIOS[scenario]
    sdk = scenario_config.sdk

    # Put the fixture into the working directory.
    scenario_fixtures: Path = FIXTURES / scenario
    provided_config_yaml = scenario_fixtures / ".bedrock_agentcore.yaml"

    if (scenario_fixtures / "src").is_dir():
        # source provided scenario
        shutil.copytree(scenario_fixtures, tmp_path, dirs_exist_ok=True)
    elif provided_config_yaml.exists():
        # config bootstrap mode scenario where there is a config file but no source code
        shutil.copy(provided_config_yaml, tmp_path / ".bedrock_agentcore.yaml")
    else:
        # nothing was provided, run bootstrap without input
        pass
    monkeypatch.chdir(tmp_path)

    project_name = "testProj"

    # patch confirm copy source prompt to yes
    with patch("bedrock_agentcore_starter_toolkit.cli.bootstrap.prompt_util.prompt", return_value="y"):
        result = test_runner.invoke(
            bootstrap_app,
            [
                "--project-name",
                project_name,
                "--iac",
                iac,
                "--sdk",
                sdk,
            ],
            catch_exceptions=False,
        )

    if result.exit_code != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    assert result.exit_code == 0

    return tmp_path / project_name, scenario_config
