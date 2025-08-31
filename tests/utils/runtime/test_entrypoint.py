"""Tests for Bedrock AgentCore utility functions."""

import pytest

from bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint import (
    detect_dependencies,
    get_python_version,
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

    def test_posix_path_delimiters_maintained_for_dockerfile(self, tmp_path):
        """Test that Posix path delimiters are maintained for Dockerfile compatibility."""
        # Create nested directory structure
        req_file, pyproject_file = self._setup_for_posix_conversion_tests(tmp_path)

        # Test requirements.txt with Posix path delimiters
        deps = detect_dependencies(tmp_path, explicit_file="dir/subdir/requirements.txt")
        assert deps.file == "dir/subdir/requirements.txt"  # Should maintain Posix style
        assert deps.resolved_path == str(req_file.resolve())  # Should maintain Posix style

        # Test pyproject.toml with Posix path delimiters
        deps = detect_dependencies(tmp_path, explicit_file="dir/subdir/pyproject.toml")
        assert deps.file == "dir/subdir/pyproject.toml"  # Should maintain Posix style
        assert deps.install_path == "dir/subdir"  # Should maintain Posix style
        assert deps.resolved_path == str(pyproject_file.resolve())  # Should maintain Posix style

    @staticmethod
    def _setup_for_posix_conversion_tests(tmp_path):
        # Create requirements,txt and pyproject.toml in nested directory structure
        subdir = tmp_path / "dir" / "subdir"
        subdir.mkdir(parents=True)

        req_file = subdir / "requirements.txt"
        req_file.write_text("bedrock_agentcore\nrequests")

        pyproject_file = subdir / "pyproject.toml"
        pyproject_file.write_text("[project]\ndependencies = ['bedrock_agentcore']")

        return req_file, pyproject_file
