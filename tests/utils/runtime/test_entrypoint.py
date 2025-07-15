"""Tests for Bedrock AgentCore utility functions."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint import (
    detect_dependencies,
    get_python_version,
    handle_requirements_file,
    parse_entrypoint,
    validate_requirements_file,
)


class TestParseEntrypoint:
    """Test parse_entrypoint function."""

    def test_parse_entrypoint_file_only(self, tmp_path):
        """Test parsing entrypoint with file only."""
        # Create a test file
        test_file = tmp_path / "test_app.py"
        test_file.write_text("# test content")

        file_path, bedrock_agentcore_name = parse_entrypoint(str(test_file))

        assert file_path == test_file.resolve()
        assert bedrock_agentcore_name == "test_app"

    def test_parse_entrypoint_file_not_found(self):
        """Test parsing entrypoint with non-existent file."""
        with pytest.raises(ValueError, match="File not found"):
            parse_entrypoint("nonexistent.py")


class TestHandleRequirementsFile:
    """Test handle_requirements_file function."""

    def test_handle_requirements_file_with_file(self, tmp_path):
        """Test with provided requirements file."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.25.1")

        with patch(
            "bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint.validate_requirements_file"
        ) as mock_validate:
            mock_deps = Mock()
            mock_validate.return_value = mock_deps

            result = handle_requirements_file(str(req_file), tmp_path)
            assert result == str(req_file)
            mock_validate.assert_called_once_with(tmp_path, str(req_file))

    def test_handle_requirements_file_validation_fails(self, tmp_path):
        """Test with invalid requirements file."""
        with patch(
            "bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint.validate_requirements_file",
            side_effect=ValueError("Invalid file"),
        ):
            with pytest.raises(ValueError, match="Invalid file"):
                handle_requirements_file("invalid.txt", tmp_path)

    def test_handle_requirements_file_auto_detect_found(self, tmp_path):
        """Test auto-detection when dependencies are found."""
        with patch("bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint.detect_dependencies") as mock_detect:
            mock_deps = Mock()
            mock_deps.found = True
            mock_deps.file = "requirements.txt"
            mock_detect.return_value = mock_deps

            result = handle_requirements_file(None, tmp_path)
            assert result is None  # Should return None to let operations handle it
            mock_detect.assert_called_once_with(tmp_path)

    def test_handle_requirements_file_auto_detect_not_found(self, tmp_path):
        """Test auto-detection when no dependencies are found."""
        with patch("bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint.detect_dependencies") as mock_detect:
            mock_deps = Mock()
            mock_deps.found = False
            mock_detect.return_value = mock_deps

            result = handle_requirements_file(None, tmp_path)
            assert result is None
            mock_detect.assert_called_once_with(tmp_path)

    def test_handle_requirements_file_default_build_dir(self):
        """Test with default build directory."""
        with patch("bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint.Path.cwd") as mock_cwd:
            mock_cwd.return_value = Path("/current/dir")

            with patch("bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint.detect_dependencies") as mock_detect:
                mock_deps = Mock()
                mock_deps.found = False
                mock_detect.return_value = mock_deps

                result = handle_requirements_file(None, None)
                assert result is None
                mock_detect.assert_called_once_with(Path("/current/dir"))


class TestDependencies:
    """Test dependency detection functionality."""

    def test_detect_dependencies_auto(self, tmp_path):
        """Test automatic detection of requirements.txt and pyproject.toml."""
        # Test no dependency files
        deps = detect_dependencies(tmp_path)
        assert not deps.found
        assert deps.type == "notfound"
        assert deps.file is None

        # Test requirements.txt detection
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("bedrock_agentcore\nrequests\nboto3")

        deps = detect_dependencies(tmp_path)
        assert deps.found
        assert deps.is_requirements
        assert deps.file == "requirements.txt"
        assert deps.resolved_path == str(req_file.resolve())
        assert not deps.is_root_package  # requirements.txt is not a root package

        # Test pyproject.toml detection (should prefer requirements.txt)
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text("""
[build-system]
requires = ["setuptools", "wheel"]

[project]
dependencies = ["bedrock_agentcore", "requests"]
""")

        deps = detect_dependencies(tmp_path)
        assert deps.found
        assert deps.is_requirements  # Still prefers requirements.txt
        assert deps.file == "requirements.txt"

        # Remove requirements.txt, should detect pyproject.toml
        req_file.unlink()
        deps = detect_dependencies(tmp_path)
        assert deps.found
        assert deps.is_pyproject
        assert deps.file == "pyproject.toml"
        assert deps.install_path == "."
        assert deps.is_root_package  # Root pyproject.toml is a root package

    def test_explicit_requirements_file(self, tmp_path):
        """Test handling of explicitly provided dependency files."""
        # Create requirements file in subdirectory
        subdir = tmp_path / "config"
        subdir.mkdir()
        req_file = subdir / "requirements.txt"
        req_file.write_text("bedrock_agentcore\nrequests")

        # Test relative path
        deps = detect_dependencies(tmp_path, explicit_file="config/requirements.txt")
        assert deps.found
        assert deps.is_requirements
        assert deps.file == "config/requirements.txt"
        assert deps.resolved_path == str(req_file.resolve())

        # Test absolute path
        deps = detect_dependencies(tmp_path, explicit_file=str(req_file.resolve()))
        assert deps.found
        assert deps.file == "config/requirements.txt"

        # Test pyproject.toml in subdirectory
        pyproject_file = subdir / "pyproject.toml"
        pyproject_file.write_text("[project]\ndependencies = ['bedrock_agentcore']")

        deps = detect_dependencies(tmp_path, explicit_file="config/pyproject.toml")
        assert deps.found
        assert deps.is_pyproject
        assert deps.install_path == "config"

        # Test file not found
        with pytest.raises(FileNotFoundError):
            detect_dependencies(tmp_path, explicit_file="nonexistent.txt")

        # Test file outside project directory
        external_file = tmp_path.parent / "external.txt"
        external_file.write_text("test")

        with pytest.raises(ValueError, match="Requirements file must be within project directory"):
            detect_dependencies(tmp_path, explicit_file=str(external_file))

    def test_validate_requirements_file(self, tmp_path):
        """Test requirements file validation."""
        # Test valid requirements.txt
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("bedrock_agentcore\nrequests")

        deps = validate_requirements_file(tmp_path, "requirements.txt")
        assert deps.found
        assert deps.file == "requirements.txt"

        # Test valid pyproject.toml
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text("[project]\ndependencies = ['bedrock_agentcore']")

        deps = validate_requirements_file(tmp_path, "pyproject.toml")
        assert deps.found
        assert deps.file == "pyproject.toml"

        # Test file not found
        with pytest.raises(FileNotFoundError):
            validate_requirements_file(tmp_path, "nonexistent.txt")

        # Test directory instead of file
        test_dir = tmp_path / "testdir"
        test_dir.mkdir()

        with pytest.raises(ValueError, match="Path is a directory, not a file"):
            validate_requirements_file(tmp_path, "testdir")

        # Test unsupported file type
        unsupported_file = tmp_path / "deps.json"
        unsupported_file.write_text('{"dependencies": []}')

        with pytest.raises(ValueError, match="not a supported dependency file"):
            validate_requirements_file(tmp_path, "deps.json")

    def test_get_python_version(self):
        """Test Python version detection."""
        version = get_python_version()
        assert isinstance(version, str)
        assert "." in version
        # Should be in format like "3.10" or "3.11"
        major, minor = version.split(".")
        assert major.isdigit()
        assert minor.isdigit()

    def test_is_root_package_property(self, tmp_path):
        """Test the is_root_package property."""
        # Test with root pyproject.toml
        pyproject_file = tmp_path / "pyproject.toml"
        pyproject_file.write_text("[project]\ndependencies = ['bedrock_agentcore']")

        deps = detect_dependencies(tmp_path)
        assert deps.is_pyproject
        assert deps.install_path == "."
        assert deps.is_root_package  # Should be True for root pyproject

        # Test with subdirectory pyproject.toml
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        sub_pyproject = subdir / "pyproject.toml"
        sub_pyproject.write_text("[project]\ndependencies = ['bedrock_agentcore']")

        deps = detect_dependencies(tmp_path, explicit_file="subdir/pyproject.toml")
        assert deps.is_pyproject
        assert deps.install_path == "subdir"
        assert not deps.is_root_package  # Should be False for subdir pyproject

        # Test with requirements.txt
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("bedrock_agentcore\nrequests")

        deps = detect_dependencies(tmp_path, explicit_file="requirements.txt")
        assert deps.is_requirements
        assert not deps.is_root_package  # Should be False for requirements files
