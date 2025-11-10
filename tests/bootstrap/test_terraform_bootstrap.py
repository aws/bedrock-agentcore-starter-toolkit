import pytest

from bedrock_agentcore_starter_toolkit.bootstrap.constants import (
    IACProvider,
)

from .test_helper.syrupy_util import snapshot_dir_tree
from .test_helper.call_bootstrap import run_bootstrap, SCENARIO_TO_SDK

# ---------------------------------------------------------------------------
# Terraform Snapshots
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("scenario", list(SCENARIO_TO_SDK.keys()))
def test_terraform_snapshots(snapshot, tmp_path, monkeypatch, scenario):
    project_dir, sdk = run_bootstrap(tmp_path, monkeypatch, scenario, IACProvider.TERRAFORM)
    assert snapshot_dir_tree(project_dir) == snapshot(name=f"{scenario}-{sdk}")