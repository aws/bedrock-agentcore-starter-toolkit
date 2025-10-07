"""Integration tests for build artifact organization."""

import tempfile
from pathlib import Path

from bedrock_agentcore_starter_toolkit.utils.runtime.schema import BuildArtifactInfo


class TestBuildArtifactOrganizationIntegration:
    """Integration tests for build artifact organization."""

    def test_artifact_directory_creation_and_organization(self):
        """Test automatic artifact directory creation and organization."""

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Test artifact directory pattern
            build_info = BuildArtifactInfo()
            artifact_dir = build_info.get_artifact_directory("test-agent")

            assert artifact_dir == ".packages/test-agent"

            # Test full artifact structure
            full_artifact_dir = temp_path / ".packages" / "test-agent"
            full_artifact_dir.mkdir(parents=True)

            # Create expected structure
            (full_artifact_dir / "src").mkdir()
            (full_artifact_dir / "Dockerfile").write_text("FROM python:3.10")

            build_info = BuildArtifactInfo(
                base_directory=str(full_artifact_dir),
                source_copy_path=str(full_artifact_dir / "src"),
                dockerfile_path=str(full_artifact_dir / "Dockerfile"),
                organized=True,
            )

            assert build_info.is_valid() is True

    def test_artifact_isolation_between_agents(self):
        """Test that artifacts are isolated between different agents."""

        agents = ["agent-1", "agent-2", "agent-3"]
        artifact_dirs = []

        for agent_name in agents:
            build_info = BuildArtifactInfo()
            artifact_dir = build_info.get_artifact_directory(agent_name)
            artifact_dirs.append(artifact_dir)

        # All directories should be different
        assert len(set(artifact_dirs)) == len(agents)

        # Each should follow expected pattern
        for i, agent_name in enumerate(agents):
            expected_dir = f".packages/{agent_name}"
            assert artifact_dirs[i] == expected_dir

    def test_artifact_cleanup_integration(self):
        """Test that artifact cleanup works properly."""

        # Create build artifacts first, then clean them up
        from bedrock_agentcore_starter_toolkit.utils.runtime.artifacts import (
            cleanup_build_artifacts,
            create_build_artifact_organization,
            get_build_artifact_info,
        )

        # Create artifacts
        artifact_info = create_build_artifact_organization("test-agent")
        assert artifact_info.organized is True

        # Verify artifacts exist
        retrieved_info = get_build_artifact_info("test-agent")
        assert retrieved_info is not None

        # Clean up artifacts
        cleanup_build_artifacts("test-agent")

        # Verify artifacts are cleaned up
        retrieved_info_after = get_build_artifact_info("test-agent")
        assert retrieved_info_after is None or not retrieved_info_after.is_valid()
