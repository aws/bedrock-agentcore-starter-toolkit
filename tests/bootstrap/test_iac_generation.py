import shutil
from pathlib import Path
import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "configs"

@pytest.mark.parametrize(
    "scenario, iac, file_to_check",
    [
        ("scenario_0", "cdk", "cdk/agent_stack.ts"),
        #("scenario_0", "tf",  "terraform/bedrock_agentcore.tf"),
        #("scenario_1", "cdk", "cdk/agent_stack.ts"),
    ],
)
def test_generator_snapshots(snapshot, tmp_path, monkeypatch, scenario, iac, file_to_check):
    # Copy fixture into working dir
    shutil.copy(FIXTURES / f"{scenario}.yaml", tmp_path / ".bedrock_agentcore.yaml")
    monkeypatch.chdir(tmp_path)

    # Run generator

    # Verify the key generated file
    content = (tmp_path / file_to_check).read_text(encoding="utf-8")
    assert content == snapshot
