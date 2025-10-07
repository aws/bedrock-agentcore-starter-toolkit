"""Tests for build artifact utilities."""

from pathlib import Path
from unittest.mock import patch

from bedrock_agentcore_starter_toolkit.utils.runtime.artifacts import (
    cleanup_build_artifacts,
    create_build_artifact_organization,
    ensure_build_artifact_directory,
)


class TestBuildArtifactOrganization:
    """Test build artifact organization utilities."""

    def test_create_build_artifact_with_source_path(self, tmp_path):
        """Test creating artifacts with source path copies files."""
        # Create source directory with test file
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "app.py").write_text("# test app")
        (source_dir / "requirements.txt").write_text("boto3==1.0.0")

        # Change to temp directory
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Create artifacts with source path (covers lines 29-33)
            artifact_info = create_build_artifact_organization("test-agent", str(source_dir))

            # Verify source was copied
            assert artifact_info.source_copy_path is not None
            base_dir = Path(artifact_info.base_directory)
            assert (base_dir / "app.py").exists()
            assert (base_dir / "requirements.txt").exists()
            assert (base_dir / "app.py").read_text() == "# test app"
        finally:
            os.chdir(original_cwd)

    def test_cleanup_build_artifacts_with_error(self, tmp_path):
        """Test cleanup handles permission errors gracefully."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Create artifacts
            create_build_artifact_organization("test-agent")

            # Mock shutil.rmtree to raise exception (covers lines 58-59)
            with patch("bedrock_agentcore_starter_toolkit.utils.runtime.artifacts.shutil.rmtree") as mock_rmtree:
                mock_rmtree.side_effect = OSError("Permission denied")

                # Should not raise, just log warning
                cleanup_build_artifacts("test-agent")
                mock_rmtree.assert_called_once()
        finally:
            os.chdir(original_cwd)

    def test_ensure_build_artifact_directory_creates_directory(self, tmp_path):
        """Test ensure_build_artifact_directory creates directory."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Covers lines 71-73
            base_dir = ensure_build_artifact_directory("test-agent")

            assert base_dir.exists()
            assert base_dir.is_dir()
            assert base_dir == Path(".bedrock-agentcore/test-agent")
        finally:
            os.chdir(original_cwd)

    def test_ensure_build_artifact_directory_idempotent(self, tmp_path):
        """Test ensure_build_artifact_directory is idempotent."""
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Call twice
            base_dir1 = ensure_build_artifact_directory("test-agent")
            base_dir2 = ensure_build_artifact_directory("test-agent")

            assert base_dir1 == base_dir2
            assert base_dir1.exists()
        finally:
            os.chdir(original_cwd)
