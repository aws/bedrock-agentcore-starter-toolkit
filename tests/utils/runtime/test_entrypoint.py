"""Tests for Bedrock AgentCore utility functions."""

import pytest

from bedrock_agentcore_starter_toolkit.utils.runtime.entrypoint import (
    TypeScriptProjectInfo,
    detect_dependencies,
    detect_entrypoint_by_language,
    detect_language,
    detect_typescript_project,
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
        # Change to temp directory to avoid finding repository files
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
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
        finally:
            os.chdir(original_cwd)

    def test_explicit_requirements_file(self, tmp_path):
        """Test handling of explicitly provided dependency files."""
        # Change to temp directory to avoid finding repository files
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
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
        finally:
            os.chdir(original_cwd)

    def test_validate_requirements_file(self, tmp_path):
        """Test requirements file validation."""
        # Change to temp directory to avoid finding repository files
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
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
        finally:
            os.chdir(original_cwd)

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
        # Change to temp directory to avoid finding repository files
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
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
        finally:
            os.chdir(original_cwd)

    def test_posix_path_delimiters_maintained_for_dockerfile(self, tmp_path):
        """Test that Posix path delimiters are maintained for Dockerfile compatibility."""
        # Change to temp directory to avoid finding repository files
        import os

        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        try:
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
        finally:
            os.chdir(original_cwd)

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


class TestDetectEntrypointByLanguage:
    """Test detect_entrypoint_by_language function."""

    def test_python_single_entrypoint(self, tmp_path):
        """Test Python detection finds single entrypoint."""
        agent_file = tmp_path / "agent.py"
        agent_file.write_text("# agent")

        result = detect_entrypoint_by_language(tmp_path, "python")
        assert len(result) == 1
        assert result[0] == agent_file

    def test_python_multiple_entrypoints(self, tmp_path):
        """Test Python detection finds all matching entrypoints."""
        (tmp_path / "agent.py").write_text("# agent")
        (tmp_path / "main.py").write_text("# main")

        result = detect_entrypoint_by_language(tmp_path, "python")
        assert len(result) == 2

    def test_python_no_entrypoint(self, tmp_path):
        """Test Python detection returns empty list when none found."""
        result = detect_entrypoint_by_language(tmp_path, "python")
        assert result == []

    def test_typescript_single_entrypoint(self, tmp_path):
        """Test TypeScript detection finds first match only."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "index.ts").write_text("// index")

        result = detect_entrypoint_by_language(tmp_path, "typescript")
        assert len(result) == 1
        assert result[0].name == "index.ts"

    def test_typescript_first_match_only(self, tmp_path):
        """Test TypeScript detection stops at first match."""
        (tmp_path / "index.ts").write_text("// index")
        (tmp_path / "agent.ts").write_text("// agent")

        result = detect_entrypoint_by_language(tmp_path, "typescript")
        assert len(result) == 1
        assert result[0].name == "index.ts"

    def test_typescript_src_priority(self, tmp_path):
        """Test TypeScript prefers src/ directory."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "index.ts").write_text("// src index")

        result = detect_entrypoint_by_language(tmp_path, "typescript")
        assert len(result) == 1
        assert "src" in str(result[0])

    def test_typescript_no_entrypoint(self, tmp_path):
        """Test TypeScript detection returns empty list when none found."""
        result = detect_entrypoint_by_language(tmp_path, "typescript")
        assert result == []


class TestDetectLanguage:
    """Test detect_language function."""

    def test_detect_language_with_package_json(self, tmp_path):
        """Test that package.json and tsconfig.json returns typescript."""
        (tmp_path / "package.json").write_text('{"name": "test"}')
        (tmp_path / "tsconfig.json").write_text("{}")

        result = detect_language(tmp_path)
        assert result == "typescript"

    def test_detect_language_package_json_only(self, tmp_path):
        """Test that package.json without tsconfig.json returns python (vanilla JS)."""
        (tmp_path / "package.json").write_text('{"name": "test"}')

        result = detect_language(tmp_path)
        assert result == "python"

    def test_detect_language_with_requirements_txt(self, tmp_path):
        """Test that requirements.txt only returns python."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests")

        result = detect_language(tmp_path)
        assert result == "python"

    def test_detect_language_empty_directory(self, tmp_path):
        """Test that empty directory returns python (default)."""
        result = detect_language(tmp_path)
        assert result == "python"

    def test_detect_language_both_files(self, tmp_path):
        """Test that package.json + tsconfig.json takes precedence."""
        (tmp_path / "package.json").write_text('{"name": "test"}')
        (tmp_path / "tsconfig.json").write_text("{}")
        (tmp_path / "requirements.txt").write_text("requests")

        result = detect_language(tmp_path)
        assert result == "typescript"


class TestDetectTypescriptProject:
    """Test detect_typescript_project function."""

    def test_full_package_json(self, tmp_path):
        """Test parsing full package.json with all fields."""
        package_json = tmp_path / "package.json"
        package_json.write_text("""{
            "name": "test-agent",
            "scripts": {"build": "tsc"},
            "engines": {"node": ">=20.0.0"}
        }""")

        result = detect_typescript_project(tmp_path)

        assert result is not None
        assert result.found
        assert result.node_version == "20"
        assert result.has_build_script is True

    def test_minimal_package_json(self, tmp_path):
        """Test parsing minimal package.json uses defaults."""
        package_json = tmp_path / "package.json"
        package_json.write_text('{"name": "test"}')

        result = detect_typescript_project(tmp_path)

        assert result is not None
        assert result.found
        assert result.node_version == "20"  # default
        assert result.has_build_script is False

    def test_no_package_json(self, tmp_path):
        """Test returns None when no package.json."""
        result = detect_typescript_project(tmp_path)
        assert result is None

    def test_node_version_caret(self, tmp_path):
        """Test parsing ^22 version string."""
        package_json = tmp_path / "package.json"
        package_json.write_text('{"engines": {"node": "^22"}}')

        result = detect_typescript_project(tmp_path)

        assert result.node_version == "22"

    def test_node_version_tilde(self, tmp_path):
        """Test parsing ~18.0.0 version string."""
        package_json = tmp_path / "package.json"
        package_json.write_text('{"engines": {"node": "~18.0.0"}}')

        result = detect_typescript_project(tmp_path)

        assert result.node_version == "18"

    def test_malformed_json(self, tmp_path):
        """Test graceful failure on malformed JSON."""
        package_json = tmp_path / "package.json"
        package_json.write_text('{"invalid json')

        result = detect_typescript_project(tmp_path)
        assert result is None


class TestTypeScriptProjectInfo:
    """Test TypeScriptProjectInfo dataclass."""

    def test_found_property_true(self):
        """Test found property when package_json_path is set."""
        info = TypeScriptProjectInfo(package_json_path="/path/to/package.json")
        assert info.found is True

    def test_found_property_false(self):
        """Test found property when package_json_path is None."""
        info = TypeScriptProjectInfo()
        assert info.found is False

    def test_default_values(self):
        """Test default values."""
        info = TypeScriptProjectInfo()
        assert info.node_version == "20"
        assert info.has_build_script is False
        assert info.package_json_path is None
