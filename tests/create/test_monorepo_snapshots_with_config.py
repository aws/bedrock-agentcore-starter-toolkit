import pytest

from bedrock_agentcore_starter_toolkit.create.constants import (
    IACProvider,
)

from .test_helper.create_scenarios import IAC_WITH_CONFIG_SCENARIOS
from .test_helper.run_create_with_config import run_create_with_config
from .test_helper.syrupy_util import snapshot_dir_tree


# CDK
@pytest.mark.parametrize("scenario", list(IAC_WITH_CONFIG_SCENARIOS.keys()))
def test_cdk_snapshots(snapshot, tmp_path, monkeypatch, scenario):
    project_dir, scenario_config = run_create_with_config(tmp_path, monkeypatch, scenario, IACProvider.CDK)
    assert snapshot_dir_tree(project_dir) == snapshot(
        name=f"{scenario}-{scenario_config.sdk}-{scenario_config.description}"
    )


# Terraform
@pytest.mark.parametrize("scenario", list(IAC_WITH_CONFIG_SCENARIOS.keys()))
def test_terraform_snapshots(snapshot, tmp_path, monkeypatch, scenario):
    project_dir, scenario_config = run_create_with_config(tmp_path, monkeypatch, scenario, IACProvider.TERRAFORM)
    assert snapshot_dir_tree(project_dir) == snapshot(
        name=f"{scenario}-{scenario_config.sdk}-{scenario_config.description}"
    )
