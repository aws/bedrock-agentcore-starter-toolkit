import shutil
from pathlib import Path
from typing import Optional

from typer.testing import CliRunner

from bedrock_agentcore_starter_toolkit.cli.create.commands import (
    create_app,
)
from bedrock_agentcore_starter_toolkit.create.constants import IACProvider

from .create_scenarios import IAC_WITH_CONFIG_SCENARIOS, ScenarioConfig

FIXTURES = Path(__file__).parent.parent / "fixtures" / "scenarios"
test_runner = CliRunner()


def run_create_with_config(tmp_path, monkeypatch, scenario, iac: Optional[IACProvider]) -> tuple[Path, ScenarioConfig]:
    """Runs the CLI generator and returns the project directory and the ScenarioConfig used"""
    scenario_config = IAC_WITH_CONFIG_SCENARIOS[scenario]
    sdk = scenario_config.sdk
    model_provider = scenario_config.modelProvider

    # Put the fixture into the working directory.
    scenario_fixtures: Path = FIXTURES / scenario
    provided_config_yaml = scenario_fixtures / ".bedrock_agentcore.yaml"

    if provided_config_yaml.exists():
        # config create mode scenario where there is a config file but no source code
        shutil.copy(provided_config_yaml, tmp_path / ".bedrock_agentcore.yaml")
    else:
        # nothing was provided, run create without input
        pass
    monkeypatch.chdir(tmp_path)

    project_name = "testProj"

    args = [
        "--project-name",
        project_name,
        "--agent-framework",
        sdk,
        "--no-venv",
        "--iac",
        iac,
        "--model-provider",
        model_provider,
    ]

    result = test_runner.invoke(
        create_app,
        args,
        catch_exceptions=False,
    )

    if result.exit_code != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
    assert result.exit_code == 0

    return tmp_path / project_name, scenario_config
