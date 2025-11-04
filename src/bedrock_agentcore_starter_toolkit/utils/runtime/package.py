"""Code zip packaging with smart dependency caching for Lambda-style deployments."""

import fnmatch
import hashlib
import logging
import os
import shutil
import subprocess  # nosec B404 - subprocess is required for pip/uv package installation
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional

import boto3

log = logging.getLogger(__name__)


class PackageCache:
    """Minimal cache for dependencies only."""

    def __init__(self, cache_dir: Path):
        """Initialize package cache.

        Args:
            cache_dir: Directory for caching artifacts (e.g., .bedrock_agentcore/{agent_name}/)
        """
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def dependencies_zip(self) -> Path:
        """Path to cached dependencies.zip (only persistent artifact)."""
        return self.cache_dir / "dependencies.zip"

    @property
    def dependencies_hash(self) -> Path:
        """Path to hash file for dependencies."""
        return self.cache_dir / "dependencies.hash"

    def should_rebuild_dependencies(
        self,
        requirements_file: Path,
        user_lock_file: Optional[Path],
        force: bool,
        runtime_version: Optional[str] = None,
    ) -> bool:
        """Determine if dependencies need rebuilding using multi-signal detection.

        Args:
            requirements_file: Source requirements file (requirements.txt or pyproject.toml)
            user_lock_file: User's uv.lock file (if exists)
            force: Force rebuild flag
            runtime_version: Python runtime version (e.g., "PYTHON_3_11")

        Returns:
            True if dependencies should be rebuilt
        """
        # Priority 1: Force flag
        if force:
            log.info("🔄 Force rebuild requested")
            return True

        # Priority 2: No cached zip
        if not self.dependencies_zip.exists():
            log.info("📦 No cached dependencies found, will build")
            return True

        # Priority 3: Combined hash of requirements + uv.lock + runtime version
        if not self.dependencies_hash.exists():
            log.info("📦 No hash file found, will rebuild")
            return True

        current_hash = self._compute_combined_hash(requirements_file, user_lock_file, runtime_version)
        stored_hash = self.dependencies_hash.read_text().strip()

        if current_hash != stored_hash:
            log.info("📦 Dependencies changed (requirements.txt, uv.lock, or runtime version), will rebuild")
            log.debug("  Previous hash: %s", stored_hash[:12])
            log.debug("  Current hash:  %s", current_hash[:12])
            return True

        log.info("✓ Using cached dependencies (no changes detected)")
        return False

    def save_dependencies_hash(
        self, requirements_file: Path, user_lock_file: Optional[Path], runtime_version: Optional[str] = None
    ) -> None:
        """Save combined hash of requirements file, uv.lock, and runtime version for future comparisons.

        Args:
            requirements_file: Source requirements file to hash
            user_lock_file: User's uv.lock file (if exists)
            runtime_version: Python runtime version (e.g., "PYTHON_3_11")
        """
        combined_hash = self._compute_combined_hash(requirements_file, user_lock_file, runtime_version)
        self.dependencies_hash.write_text(combined_hash)

    @staticmethod
    def _compute_file_hash(file_path: Path) -> str:
        """Compute SHA256 hash of file.

        Args:
            file_path: File to hash

        Returns:
            SHA256 hash as hex string
        """
        return hashlib.sha256(file_path.read_bytes()).hexdigest()

    def _compute_combined_hash(
        self, requirements_file: Path, user_lock_file: Optional[Path], runtime_version: Optional[str] = None
    ) -> str:
        """Compute combined hash of requirements file, uv.lock, and runtime version.

        Args:
            requirements_file: Source requirements file
            user_lock_file: User's uv.lock file (if exists)
            runtime_version: Python runtime version (e.g., "PYTHON_3_11")

        Returns:
            Combined SHA256 hash as hex string
        """
        req_hash = self._compute_file_hash(requirements_file)

        # Build hash components
        hash_components = [req_hash]

        if user_lock_file and user_lock_file.exists():
            lock_hash = self._compute_file_hash(user_lock_file)
            hash_components.append(lock_hash)

        if runtime_version:
            hash_components.append(runtime_version)

        # Combine all components deterministically
        combined_input = ":".join(hash_components)
        combined_hash = hashlib.sha256(combined_input.encode()).hexdigest()

        log.debug(
            "Hash components: requirements=%s, lock=%s, runtime=%s",
            bool(requirements_file),
            bool(user_lock_file and user_lock_file.exists()),
            bool(runtime_version),
        )
        return combined_hash


class CodeZipPackager:
    """Creates Lambda-style deployment packages with smart caching."""

    def create_deployment_package(
        self,
        source_dir: Path,
        agent_name: str,
        cache_dir: Path,
        runtime_version: str,
        requirements_file: Optional[Path] = None,
        force_rebuild_deps: bool = False,
    ) -> tuple[Path, bool]:
        """Create deployment.zip with smart dependency caching.

        Flow:
        1. Check cache for dependencies.zip (or rebuild if needed)
        2. Build code.zip in temp dir
        3. Merge → deployment.zip in temp dir
        4. Return path to deployment.zip (caller uploads to S3 and cleans up)

        Args:
            source_dir: Directory containing source code
            agent_name: Name of the agent
            cache_dir: Cache directory for dependencies
            runtime_version: Python runtime version (e.g., "python3.10")
            requirements_file: Path to requirements.txt or pyproject.toml
            force_rebuild_deps: Force rebuild of dependencies even if cached

        Returns:
            Tuple of (deployment_zip_path, has_otel_distro)
            - deployment_zip_path: Path to deployment.zip in temp directory
            - has_otel_distro: True if aws-opentelemetry-distro is installed
        """
        cache = PackageCache(cache_dir)

        # Step 1: Ensure dependencies.zip exists in cache
        has_dependencies = requirements_file is not None and requirements_file.exists()

        if has_dependencies and requirements_file is not None:  # Type guard for mypy
            user_lock = source_dir / "uv.lock"

            needs_rebuild = cache.should_rebuild_dependencies(
                requirements_file, user_lock if user_lock.exists() else None, force_rebuild_deps, runtime_version
            )

            if needs_rebuild:
                log.info("Building dependencies (this may take a minute)...")
                self._build_dependencies_zip(requirements_file, cache.dependencies_zip, runtime_version)
                cache.save_dependencies_hash(
                    requirements_file, user_lock if user_lock.exists() else None, runtime_version
                )
                log.info("✓ Dependencies cached")

        # Step 2: Create ephemeral code.zip and deployment.zip in temp
        temp_dir = Path(tempfile.mkdtemp(prefix=f"agentcore_{agent_name}_"))

        try:
            direct_code_deploy = temp_dir / "code.zip"
            deployment_zip = temp_dir / "deployment.zip"

            log.info("Packaging source code...")
            self._build_direct_code_deploy(source_dir, direct_code_deploy)

            log.info("Creating deployment package...")
            self._merge_zips(cache.dependencies_zip if has_dependencies else None, direct_code_deploy, deployment_zip)

            # Validate size
            size_mb = deployment_zip.stat().st_size / (1024 * 1024)
            log.info("✓ Deployment package ready: %.2f MB", size_mb)

            if size_mb > 250:
                log.warning("⚠️  Package size (%.2f MB) exceeds 250MB limit. Consider reducing dependencies.", size_mb)

            # Check if aws-opentelemetry-distro is present for instrumentation
            has_otel_distro = self._check_otel_distro(requirements_file)

            return deployment_zip, has_otel_distro

        except Exception:
            # Cleanup temp on error
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

    def _build_dependencies_zip(self, requirements_file: Path, output_zip: Path, runtime_version: str) -> None:
        """Build dependencies.zip to cache (expensive operation).

        Args:
            requirements_file: Source requirements file
            output_zip: Path to output dependencies.zip
            runtime_version: Python runtime version
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir) / "package"
            package_dir.mkdir()

            # Handle pyproject.toml → requirements.txt conversion
            # (necessary because uv pip install --target requires -r flag)
            if requirements_file.name == "pyproject.toml":
                resolved_reqs = self._resolve_pyproject_to_requirements(requirements_file, Path(temp_dir))
            else:
                resolved_reqs = requirements_file

            # Install dependencies (uv only)
            cross_compile = self._should_cross_compile()
            self._install_dependencies(resolved_reqs, package_dir, runtime_version, cross_compile)

            # Create zip (keep metadata for proper package resolution)
            log.info("Creating dependencies.zip...")
            with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(package_dir):
                    # Filter out __pycache__ directories
                    dirs[:] = [d for d in dirs if d != "__pycache__"]

                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(package_dir)
                        zipf.write(file_path, arcname)

    def _check_otel_distro(self, requirements_file: Optional[Path]) -> bool:
        """Check if aws-opentelemetry-distro is in requirements.

        Args:
            requirements_file: Path to requirements file (requirements.txt or pyproject.toml)

        Returns:
            True if aws-opentelemetry-distro is found
        """
        if not requirements_file or not requirements_file.exists():
            return False

        try:
            content = requirements_file.read_text()
            # Check for OpenTelemetry packages in requirements
            return "aws-opentelemetry-distro" in content or "opentelemetry-instrumentation" in content
        except Exception as e:
            log.debug("Could not check requirements for OpenTelemetry: %s", e)
            return False

    def _resolve_pyproject_to_requirements(self, pyproject_file: Path, output_dir: Path) -> Path:
        """Convert pyproject.toml to requirements.txt using uv.

        Args:
            pyproject_file: Path to pyproject.toml
            output_dir: Directory for output requirements.txt

        Returns:
            Path to resolved requirements.txt

        Raises:
            RuntimeError: If uv is not available or compilation fails
        """
        if not shutil.which("uv"):
            raise RuntimeError(
                "uv is required for resolving pyproject.toml but was not found.\n"
                "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
            )

        output_file = output_dir / "requirements.txt"

        log.info("Resolving pyproject.toml with uv...")
        try:
            subprocess.run(  # nosec B603 B607 - using hardcoded command "uv" without shell=True
                [
                    "uv",
                    "pip",
                    "compile",
                    str(pyproject_file),
                    "--output-file",
                    str(output_file),
                    "--quiet",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            log.info("✓ Dependencies resolved with uv")
            return output_file
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to resolve pyproject.toml with uv: {e.stderr}") from e

    def _install_dependencies(
        self, requirements_file: Path, target_dir: Path, runtime_version: str, cross_compile: bool
    ) -> None:
        """Install dependencies using uv only.

        Args:
            requirements_file: Path to requirements.txt
            target_dir: Target directory for installation
            runtime_version: Python runtime version (e.g., "PYTHON_3_10" or "python3.10")
            cross_compile: Whether to cross-compile for ARM64

        Raises:
            RuntimeError: If uv is not available or installation fails
        """
        if not shutil.which("uv"):
            raise RuntimeError(
                "uv is required for installing dependencies but was not found.\n"
                "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
            )

        # Normalize python version to X.Y format (e.g., "3.10")
        # Input: "PYTHON_3_10" or "python3.10" → Output: "3.10"
        python_version = runtime_version.upper().replace("PYTHON", "").replace("_", ".").strip("_. ")

        cmd = self._build_uv_command(requirements_file, target_dir, python_version, cross_compile)
        log.info("Installing dependencies with uv%s...", " (cross-compiling for Linux ARM64)" if cross_compile else "")

        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)  # nosec B603 - using uv command
            log.info("✓ Dependencies installed with uv")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to install dependencies with uv: {e.stderr}") from e

    def _build_uv_command(self, requirements: Path, target: Path, py_version: str, cross: bool) -> List[str]:
        """Build uv pip install command.

        Args:
            requirements: Path to requirements.txt
            target: Target directory
            py_version: Python version (e.g., "3.10")
            cross: Whether to cross-compile

        Returns:
            Command as list of strings
        """
        cmd = [
            "uv",
            "pip",
            "install",
            "--target",
            str(target),
            "--python-version",
            py_version,
        ]

        # Always use aarch64-manylinux2014 for AgentCore Runtime (ARM64)
        # Note: uv uses --python-platform (not --platform like pip)
        if cross:
            cmd.extend(
                [
                    "--python-platform",
                    "aarch64-manylinux2014",
                    "--only-binary",
                    ":all:",
                ]
            )

        cmd.extend(["--upgrade", "-r", str(requirements)])
        return cmd

    def _should_cross_compile(self) -> bool:
        """Check if cross-compilation is needed for ARM64.

        AgentCore Runtime always requires Linux ARM64 binaries (manylinux2014_aarch64),
        regardless of host platform. Always return True to ensure correct platform targeting.

        Returns:
            Always True - force platform-specific builds for AgentCore Runtime
        """
        log.info("Building dependencies for Linux ARM64 Runtime (manylinux2014_aarch64)")
        return True

    def _build_direct_code_deploy(self, source_dir: Path, output_zip: Path) -> None:
        """Build code.zip with source files (respects ignore patterns).

        Args:
            source_dir: Source directory
            output_zip: Path to output code.zip
        """
        ignore_patterns = self._get_ignore_patterns()

        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_dir):
                rel_root = os.path.relpath(root, source_dir)
                if rel_root == ".":
                    rel_root = ""

                # Filter directories
                dirs[:] = [
                    d
                    for d in dirs
                    if not self._should_ignore(os.path.join(rel_root, d) if rel_root else d, ignore_patterns, True)
                ]

                # Add files
                for file in files:
                    file_rel = os.path.join(rel_root, file) if rel_root else file

                    if self._should_ignore(file_rel, ignore_patterns, False):
                        continue

                    zipf.write(Path(root) / file, file_rel)

    def _merge_zips(self, dependencies_zip: Optional[Path], direct_code_deploy: Path, output_zip: Path) -> None:
        """Merge dependencies and code layers into deployment.zip.

        Args:
            dependencies_zip: Path to dependencies.zip (optional)
            direct_code_deploy: Path to code.zip
            output_zip: Path to output deployment.zip
        """
        with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as out:
            # Layer 1: Dependencies
            if dependencies_zip and dependencies_zip.exists():
                with zipfile.ZipFile(dependencies_zip, "r") as dep:
                    for item in dep.namelist():
                        out.writestr(item, dep.read(item))

            # Layer 2: Code (overwrites conflicts - user code takes precedence)
            with zipfile.ZipFile(direct_code_deploy, "r") as code:
                for item in code.namelist():
                    out.writestr(item, code.read(item))

    def _get_ignore_patterns(self) -> List[str]:
        """Get ignore patterns from dockerignore.template (matches CodeBuild logic).

        Returns:
            List of dockerignore patterns
        """
        try:
            from importlib.resources import files

            template_content = (
                files("bedrock_agentcore_starter_toolkit")
                .joinpath("utils/runtime/templates/dockerignore.template")
                .read_text()
            )

            patterns = []
            for line in template_content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)

            log.debug("Using dockerignore.template with %d patterns for code.zip", len(patterns))
            return patterns

        except Exception as e:
            # Fallback to minimal default patterns if template not found
            log.warning("Could not load dockerignore.template (%s), using minimal default patterns", e)
            return [
                ".git",
                "__pycache__",
                "*.pyc",
                ".DS_Store",
                "node_modules",
                ".venv",
                "venv",
                "*.egg-info",
                ".bedrock_agentcore",
            ]

    def _should_ignore(self, path: str, patterns: List[str], is_dir: bool) -> bool:
        """Check if path should be ignored based on dockerignore patterns.

        Args:
            path: Path to check
            patterns: List of dockerignore patterns
            is_dir: Whether path is a directory

        Returns:
            True if path should be ignored
        """
        # Normalize path
        if path.startswith("./"):
            path = path[2:]

        should_ignore = False

        for pattern in patterns:
            # Handle negation patterns
            if pattern.startswith("!"):
                if self._matches_pattern(path, pattern[1:], is_dir):
                    should_ignore = False
            else:
                if self._matches_pattern(path, pattern, is_dir):
                    should_ignore = True

        return should_ignore

    def _matches_pattern(self, path: str, pattern: str, is_dir: bool) -> bool:
        """Check if path matches a dockerignore pattern.

        Args:
            path: Path to check
            pattern: Dockerignore pattern
            is_dir: Whether path is a directory

        Returns:
            True if path matches pattern
        """
        # Directory-specific patterns
        if pattern.endswith("/"):
            if not is_dir:
                return False
            pattern = pattern[:-1]

        # Exact match
        if path == pattern:
            return True

        # Wildcard matching
        if fnmatch.fnmatch(path, pattern):
            return True

        # Match directory prefix
        if is_dir and pattern in path.split("/"):
            return True

        return False

    def upload_to_s3(self, deployment_zip: Path, agent_name: str, session: boto3.Session, account_id: str) -> str:
        """Upload deployment.zip to S3 (reuses CodeBuild bucket infrastructure).

        Args:
            deployment_zip: Path to deployment.zip
            agent_name: Name of the agent
            session: Boto3 session
            account_id: AWS account ID (from config)

        Returns:
            S3 location (s3://bucket/key)
        """
        from ...services.codebuild import CodeBuildService

        codebuild = CodeBuildService(session)

        bucket = codebuild.ensure_source_bucket(account_id)

        s3_key = f"{agent_name}/deployment.zip"
        s3 = session.client("s3")

        log.info("Uploading to s3://%s/%s...", bucket, s3_key)
        s3.upload_file(str(deployment_zip), bucket, s3_key, ExtraArgs={"ExpectedBucketOwner": account_id})

        return f"s3://{bucket}/{s3_key}"
