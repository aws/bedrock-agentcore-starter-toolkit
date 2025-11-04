"""Tests for code zip packaging with dependency caching."""

import hashlib
import zipfile
from unittest.mock import Mock, patch

from bedrock_agentcore_starter_toolkit.utils.runtime.package import CodeZipPackager, PackageCache


class TestPackageCache:
    """Test PackageCache functionality."""

    def test_init_creates_cache_dir(self, tmp_path):
        """Test cache directory creation."""
        cache_dir = tmp_path / "cache"
        cache = PackageCache(cache_dir)

        assert cache.cache_dir == cache_dir
        assert cache_dir.exists()

    def test_dependencies_zip_path(self, tmp_path):
        """Test dependencies.zip path property."""
        cache = PackageCache(tmp_path)
        assert cache.dependencies_zip == tmp_path / "dependencies.zip"

    def test_dependencies_hash_path(self, tmp_path):
        """Test dependencies.hash path property."""
        cache = PackageCache(tmp_path)
        assert cache.dependencies_hash == tmp_path / "dependencies.hash"

    def test_should_rebuild_force_flag(self, tmp_path):
        """Test force rebuild flag."""
        cache = PackageCache(tmp_path)
        reqs = tmp_path / "requirements.txt"
        reqs.write_text("flask==2.0.0\n")

        # Force flag should always return True
        assert cache.should_rebuild_dependencies(reqs, None, force=True) is True

    def test_should_rebuild_no_cached_zip(self, tmp_path):
        """Test rebuild when no cached zip exists."""
        cache = PackageCache(tmp_path)
        reqs = tmp_path / "requirements.txt"
        reqs.write_text("flask==2.0.0\n")

        assert cache.should_rebuild_dependencies(reqs, None, force=False) is True

    def test_should_rebuild_no_hash_file(self, tmp_path):
        """Test rebuild when hash file missing."""
        cache = PackageCache(tmp_path)
        reqs = tmp_path / "requirements.txt"
        reqs.write_text("flask==2.0.0\n")

        # Create zip but no hash
        cache.dependencies_zip.write_text("fake zip")

        assert cache.should_rebuild_dependencies(reqs, None, force=False) is True

    def test_should_rebuild_hash_mismatch(self, tmp_path):
        """Test rebuild when requirements hash changed."""
        cache = PackageCache(tmp_path)
        reqs = tmp_path / "requirements.txt"
        reqs.write_text("flask==2.0.0\n")

        # Setup cache with old hash
        cache.dependencies_zip.write_text("fake zip")
        cache.dependencies_hash.write_text("old_hash")

        assert cache.should_rebuild_dependencies(reqs, None, force=False) is True

    def test_should_rebuild_uv_lock_changes(self, tmp_path):
        """Test rebuild when uv.lock content changes."""
        cache = PackageCache(tmp_path)
        reqs = tmp_path / "requirements.txt"
        reqs.write_text("flask==2.0.0\n")

        lock_file = tmp_path / "uv.lock"
        lock_file.write_text("# original lock content\n")

        # Create cached zip and hash with original lock
        cache.dependencies_zip.write_text("fake zip")
        cache.save_dependencies_hash(reqs, lock_file)

        # Modify uv.lock content (changes hash)
        lock_file.write_text("# modified lock content\n")

        # Should rebuild due to uv.lock hash change
        assert cache.should_rebuild_dependencies(reqs, lock_file, force=False) is True

    def test_should_not_rebuild_when_cached(self, tmp_path):
        """Test no rebuild when cache is valid."""
        cache = PackageCache(tmp_path)
        reqs = tmp_path / "requirements.txt"
        reqs.write_text("flask==2.0.0\n")

        # Setup valid cache (no uv.lock)
        cache.dependencies_zip.write_text("fake zip")
        cache.save_dependencies_hash(reqs, None)

        assert cache.should_rebuild_dependencies(reqs, None, force=False) is False

    def test_should_not_rebuild_when_cached_with_lock(self, tmp_path):
        """Test no rebuild when cache is valid with uv.lock."""
        cache = PackageCache(tmp_path)
        reqs = tmp_path / "requirements.txt"
        reqs.write_text("flask==2.0.0\n")

        lock = tmp_path / "uv.lock"
        lock.write_text("# lock content\n")

        # Setup valid cache with lock
        cache.dependencies_zip.write_text("fake zip")
        cache.save_dependencies_hash(reqs, lock)

        # No changes - should not rebuild
        assert cache.should_rebuild_dependencies(reqs, lock, force=False) is False

    def test_save_dependencies_hash(self, tmp_path):
        """Test saving dependencies hash (requirements only)."""
        cache = PackageCache(tmp_path)
        reqs = tmp_path / "requirements.txt"
        reqs.write_text("flask==2.0.0\n")

        cache.save_dependencies_hash(reqs, None)

        assert cache.dependencies_hash.exists()
        stored_hash = cache.dependencies_hash.read_text().strip()

        # Calculate expected hash: just requirements file hash since no lock file or runtime
        req_hash = hashlib.sha256(reqs.read_bytes()).hexdigest()
        combined_input = req_hash  # Only requirements hash, no lock file or runtime
        expected_hash = hashlib.sha256(combined_input.encode()).hexdigest()

        assert stored_hash == expected_hash

    def test_save_dependencies_hash_with_lock(self, tmp_path):
        """Test saving combined hash with uv.lock."""
        cache = PackageCache(tmp_path)
        reqs = tmp_path / "requirements.txt"
        reqs.write_text("flask==2.0.0\n")
        lock = tmp_path / "uv.lock"
        lock.write_text("# uv.lock content\nflask==2.0.0\n")

        cache.save_dependencies_hash(reqs, lock)

        assert cache.dependencies_hash.exists()
        stored_hash = cache.dependencies_hash.read_text().strip()

        # Verify it's a combined hash (different from single file hash)
        req_hash = hashlib.sha256(reqs.read_bytes()).hexdigest()
        assert stored_hash != req_hash  # Should be different due to combining

    def test_compute_file_hash(self, tmp_path):
        """Test file hash computation."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        file_hash = PackageCache._compute_file_hash(test_file)
        expected = hashlib.sha256(b"test content").hexdigest()

        assert file_hash == expected


class TestCodeZipPackager:
    """Test CodeZipPackager functionality."""

    def test_create_deployment_package_no_requirements(self, tmp_path):
        """Test creating deployment package without requirements."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "agent.py").write_text("print('hello')")

        cache_dir = tmp_path / "cache"
        packager = CodeZipPackager()

        result, has_otel = packager.create_deployment_package(
            source_dir=source_dir,
            agent_name="test-agent",
            cache_dir=cache_dir,
            runtime_version="python3.10",
            requirements_file=None,
        )

        assert result.exists()
        assert result.name == "deployment.zip"
        assert has_otel is False

        # Verify zip contains code
        with zipfile.ZipFile(result, "r") as zf:
            assert "agent.py" in zf.namelist()

    @patch("bedrock_agentcore_starter_toolkit.utils.runtime.package.CodeZipPackager._build_dependencies_zip")
    def test_create_deployment_package_with_requirements(self, mock_build_deps, tmp_path):
        """Test creating deployment package with requirements."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "agent.py").write_text("print('hello')")

        reqs = tmp_path / "requirements.txt"
        reqs.write_text("flask==2.0.0\n")

        cache_dir = tmp_path / "cache"
        cache_dir.mkdir()

        # Mock dependencies.zip in cache
        deps_zip = cache_dir / "dependencies.zip"
        with zipfile.ZipFile(deps_zip, "w") as zf:
            zf.writestr("flask/__init__.py", "# flask")

        packager = CodeZipPackager()
        result, has_otel = packager.create_deployment_package(
            source_dir=source_dir,
            agent_name="test-agent",
            cache_dir=cache_dir,
            runtime_version="python3.10",
            requirements_file=reqs,
            force_rebuild_deps=True,  # Force rebuild to test path
        )

        assert result.exists()
        assert has_otel is False  # flask doesn't include OpenTelemetry
        mock_build_deps.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.utils.runtime.package.CodeZipPackager._build_dependencies_zip")
    def test_create_deployment_package_size_check(self, mock_build_deps, tmp_path, caplog):
        """Test size check for deployment packages."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        (source_dir / "agent.py").write_text("print('hello')")

        cache_dir = tmp_path / "cache"
        packager = CodeZipPackager()

        result, has_otel = packager.create_deployment_package(
            source_dir=source_dir,
            agent_name="test-agent",
            cache_dir=cache_dir,
            runtime_version="python3.10",
        )

        assert result.exists()
        assert has_otel is False
        # Just verify the package was created successfully
        size_mb = result.stat().st_size / (1024 * 1024)
        assert size_mb < 250  # Should be small without dependencies

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_resolve_pyproject_with_uv(self, mock_which, mock_run, tmp_path):
        """Test pyproject.toml resolution with uv."""
        mock_which.return_value = "/usr/local/bin/uv"
        mock_run.return_value = Mock(returncode=0)

        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"\ndependencies = ["flask==2.0.0"]\n')

        output_dir = tmp_path / "output"
        output_dir.mkdir()

        packager = CodeZipPackager()
        result = packager._resolve_pyproject_to_requirements(pyproject, output_dir)

        assert result == output_dir / "requirements.txt"
        mock_run.assert_called_once()
        assert "uv" in mock_run.call_args[0][0]

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_install_dependencies_with_uv(self, mock_which, mock_run, tmp_path):
        """Test dependency installation with uv."""
        mock_which.return_value = "/usr/local/bin/uv"
        mock_run.return_value = Mock(returncode=0)

        reqs = tmp_path / "requirements.txt"
        reqs.write_text("flask==2.0.0\n")

        target = tmp_path / "target"
        target.mkdir()

        packager = CodeZipPackager()
        packager._install_dependencies(reqs, target, "python3.10", cross_compile=False)

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "uv" in cmd
        assert "--python-version" in cmd
        assert "3.10" in cmd

    def test_build_uv_command(self, tmp_path):
        """Test uv command building."""
        reqs = tmp_path / "requirements.txt"
        target = tmp_path / "target"

        packager = CodeZipPackager()
        cmd = packager._build_uv_command(reqs, target, "3.10", cross=False)

        assert "uv" in cmd
        assert "--python-version" in cmd
        assert "3.10" in cmd
        assert "--target" in cmd
        assert str(target) in cmd

    def test_build_uv_command_with_cross_compile(self, tmp_path):
        """Test uv command with cross-compilation."""
        reqs = tmp_path / "requirements.txt"
        target = tmp_path / "target"

        packager = CodeZipPackager()
        cmd = packager._build_uv_command(reqs, target, "3.10", cross=True)

        assert "--python-platform" in cmd
        assert "aarch64-manylinux2014" in cmd
        assert "--only-binary" in cmd

    def test_should_cross_compile(self):
        """Test cross-compilation detection."""
        packager = CodeZipPackager()
        # Always returns True for AgentCore Runtime
        assert packager._should_cross_compile() is True

    def test_build_direct_code_deploy(self, tmp_path):
        """Test code zip creation."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create test files
        (source_dir / "agent.py").write_text("print('hello')")
        (source_dir / "utils.py").write_text("def helper(): pass")

        # Create ignored files
        (source_dir / "test.pyc").write_text("compiled")
        pycache = source_dir / "__pycache__"
        pycache.mkdir()
        (pycache / "agent.cpython-310.pyc").write_text("compiled")

        output_zip = tmp_path / "code.zip"

        packager = CodeZipPackager()
        packager._build_direct_code_deploy(source_dir, output_zip)

        with zipfile.ZipFile(output_zip, "r") as zf:
            names = zf.namelist()
            # Should include source files
            assert "agent.py" in names
            assert "utils.py" in names
            # Should not include ignored files
            assert "test.pyc" not in names
            assert "__pycache__/agent.cpython-310.pyc" not in names

    def test_build_direct_code_deploy_with_subdirs(self, tmp_path):
        """Test code zip with subdirectories."""
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create nested structure
        (source_dir / "agent.py").write_text("print('hello')")
        utils_dir = source_dir / "utils"
        utils_dir.mkdir()
        (utils_dir / "helper.py").write_text("def help(): pass")

        output_zip = tmp_path / "code.zip"

        packager = CodeZipPackager()
        packager._build_direct_code_deploy(source_dir, output_zip)

        with zipfile.ZipFile(output_zip, "r") as zf:
            names = zf.namelist()
            assert "agent.py" in names
            assert "utils/helper.py" in names

    def test_merge_zips_with_dependencies(self, tmp_path):
        """Test merging dependencies and code zips."""
        # Create dependencies.zip
        deps_zip = tmp_path / "dependencies.zip"
        with zipfile.ZipFile(deps_zip, "w") as zf:
            zf.writestr("flask/__init__.py", "# flask")
            zf.writestr("requests/__init__.py", "# requests")

        # Create code.zip
        direct_code_deploy = tmp_path / "code.zip"
        with zipfile.ZipFile(direct_code_deploy, "w") as zf:
            zf.writestr("agent.py", "print('hello')")

        output_zip = tmp_path / "deployment.zip"

        packager = CodeZipPackager()
        packager._merge_zips(deps_zip, direct_code_deploy, output_zip)

        with zipfile.ZipFile(output_zip, "r") as zf:
            names = zf.namelist()
            # Should have both dependencies and code
            assert "flask/__init__.py" in names
            assert "requests/__init__.py" in names
            assert "agent.py" in names

    def test_merge_zips_code_overwrites_dependencies(self, tmp_path):
        """Test that code overwrites conflicting dependencies."""
        # Create dependencies.zip with shared file
        deps_zip = tmp_path / "dependencies.zip"
        with zipfile.ZipFile(deps_zip, "w") as zf:
            zf.writestr("config.py", "SETTING = 'dependency'")

        # Create code.zip with same file
        direct_code_deploy = tmp_path / "code.zip"
        with zipfile.ZipFile(direct_code_deploy, "w") as zf:
            zf.writestr("config.py", "SETTING = 'user'")

        output_zip = tmp_path / "deployment.zip"

        packager = CodeZipPackager()
        packager._merge_zips(deps_zip, direct_code_deploy, output_zip)

        with zipfile.ZipFile(output_zip, "r") as zf:
            content = zf.read("config.py").decode()
            # User code should win
            assert "SETTING = 'user'" in content

    def test_merge_zips_without_dependencies(self, tmp_path):
        """Test merging with no dependencies."""
        direct_code_deploy = tmp_path / "code.zip"
        with zipfile.ZipFile(direct_code_deploy, "w") as zf:
            zf.writestr("agent.py", "print('hello')")

        output_zip = tmp_path / "deployment.zip"

        packager = CodeZipPackager()
        packager._merge_zips(None, direct_code_deploy, output_zip)

        with zipfile.ZipFile(output_zip, "r") as zf:
            names = zf.namelist()
            assert "agent.py" in names

    def test_get_ignore_patterns(self):
        """Test ignore patterns (loaded from dockerignore.template)."""
        packager = CodeZipPackager()
        patterns = packager._get_ignore_patterns()

        # Should contain key patterns from dockerignore.template
        assert any("pycache" in p.lower() for p in patterns)
        assert any("git" in p.lower() for p in patterns)
        assert any("bedrock_agentcore" in p.lower() for p in patterns)

    def test_should_ignore_file(self):
        """Test file ignore detection."""
        packager = CodeZipPackager()
        patterns = ["*.pyc", "__pycache__/", ".git/"]

        # Should ignore
        assert packager._should_ignore("test.pyc", patterns, False) is True
        assert packager._should_ignore("module.pyc", patterns, False) is True

        # Should not ignore
        assert packager._should_ignore("test.py", patterns, False) is False

    def test_should_ignore_directory(self):
        """Test directory ignore detection."""
        packager = CodeZipPackager()
        patterns = ["__pycache__/", ".git/"]

        # Should ignore
        assert packager._should_ignore("__pycache__", patterns, True) is True
        assert packager._should_ignore(".git", patterns, True) is True

        # Should not ignore
        assert packager._should_ignore("utils", patterns, True) is False

    @patch("bedrock_agentcore_starter_toolkit.services.codebuild.CodeBuildService")
    def test_upload_to_s3(self, mock_codebuild_class, tmp_path):
        """Test S3 upload."""
        deployment_zip = tmp_path / "deployment.zip"
        deployment_zip.write_bytes(b"fake zip")

        mock_session = Mock()
        mock_s3 = Mock()
        mock_session.client.return_value = mock_s3

        mock_codebuild = Mock()
        mock_codebuild.ensure_source_bucket.return_value = "test-bucket"
        mock_codebuild_class.return_value = mock_codebuild

        packager = CodeZipPackager()
        result = packager.upload_to_s3(
            deployment_zip=deployment_zip,
            agent_name="test-agent",
            session=mock_session,
            account_id="123456789012",
        )

        assert result == "s3://test-bucket/test-agent/deployment.zip"
        mock_codebuild.ensure_source_bucket.assert_called_once_with("123456789012")
        mock_s3.upload_file.assert_called_once()

    def test_runtime_version_normalization(self, tmp_path):
        """Test Python version normalization in uv commands."""
        packager = CodeZipPackager()
        reqs = tmp_path / "requirements.txt"
        target = tmp_path / "target"

        # Note: Normalization happens in _install_dependencies before calling _build_uv_command
        # This method receives already-normalized versions (e.g., "3.10")
        cmd1 = packager._build_uv_command(reqs, target, "3.10", cross=False)
        assert "--python-version" in cmd1
        assert "3.10" in cmd1

        cmd2 = packager._build_uv_command(reqs, target, "3.11", cross=False)
        assert "--python-version" in cmd2
        assert "3.11" in cmd2

        cmd3 = packager._build_uv_command(reqs, target, "3.12", cross=True)
        assert "--python-version" in cmd3
        assert "3.12" in cmd3
        assert "--python-platform" in cmd3
        assert "aarch64-manylinux2014" in cmd3
