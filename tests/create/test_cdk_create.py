import pytest

from bedrock_agentcore_starter_toolkit.create.constants import (
    IACProvider,
)

from .test_helper.create_scenarios import IAC_SCENARIOS
from .test_helper.run_create import run_create
from .test_helper.syrupy_util import snapshot_dir_tree

# ---------------------------------------------------------------------------
# CDK Snapshots
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("scenario", list(IAC_SCENARIOS.keys()))
def test_cdk_snapshots(snapshot, tmp_path, monkeypatch, scenario):
    project_dir, scenario_config = run_create(tmp_path, monkeypatch, scenario, IACProvider.CDK)
    assert snapshot_dir_tree(project_dir) == snapshot(
        name=f"{scenario}-{scenario_config.sdk}-{scenario_config.description}"
    )
