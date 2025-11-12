import pytest

from bedrock_agentcore_starter_toolkit.bootstrap.constants import (
    IACProvider,
)

from .test_helper.bootstrap_scenarios import SCENARIOS
from .test_helper.run_bootstrap import run_bootstrap
from .test_helper.syrupy_util import snapshot_dir_tree

# ---------------------------------------------------------------------------
# Terraform Snapshots
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario", list(SCENARIOS.keys()))
def test_cdk_snapshots(snapshot, tmp_path, monkeypatch, scenario):
    project_dir, scenario_config = run_bootstrap(tmp_path, monkeypatch, scenario, IACProvider.TERRAFORM)
    assert snapshot_dir_tree(project_dir) == snapshot(
        name=f"{scenario}-{scenario_config.sdk}-{scenario_config.description}"
    )
