"""CodeBuild service for ARM64 container builds."""

import fnmatch
import logging
import os
import tempfile
import time
import zipfile
from pathlib import Path
from typing import List

import boto3
from botocore.exceptions import ClientError

from ..operations.runtime.create_role import get_or_create_codebuild_execution_role


class CodeBuildService:
    """Service for managing CodeBuild projects and builds for ARM64."""

    def __init__(self, session: boto3.Session):
        """Initialize CodeBuild service with AWS session."""
        self.session = session
        self.client = session.client("codebuild")
        self.s3_client = session.client("s3")
        self.iam_client = session.client("iam")
        self.logger = logging.getLogger(__name__)
        self.source_bucket = None

    def get_source_bucket_name(self, account_id: str) -> str:
        """Get S3 bucket name for CodeBuild sources."""
        region = self.session.region_name
        return f"bedrock-agentcore-codebuild-sources-{account_id}-{region}"

    def ensure_source_bucket(self, account_id: str) -> str:
        """Ensure S3 bucket exists for CodeBuild sources."""
        bucket_name = self.get_source_bucket_name(account_id)

        try:
            self.s3_client.head_bucket(Bucket=bucket_name)
            self.logger.debug("Using existing S3 bucket: %s", bucket_name)
        except ClientError:
            # Create bucket
            region = self.session.region_name
            if region == "us-east-1":
                self.s3_client.create_bucket(Bucket=bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=bucket_name, CreateBucketConfiguration={"LocationConstraint": region}
                )

            # Set lifecycle to cleanup old builds
            self.s3_client.put_bucket_lifecycle_configuration(
                Bucket=bucket_name,
                LifecycleConfiguration={
                    "Rules": [{"ID": "DeleteOldBuilds", "Status": "Enabled", "Filter": {}, "Expiration": {"Days": 7}}]
                },
            )

            self.logger.info("Created S3 bucket: %s", bucket_name)

        return bucket_name

    def upload_source(self, agent_name: str) -> str:
        """Upload current directory to S3, respecting .dockerignore patterns."""
        account_id = self.session.client("sts").get_caller_identity()["Account"]
        bucket_name = self.ensure_source_bucket(account_id)
        self.source_bucket = bucket_name

        # Parse .dockerignore patterns
        ignore_patterns = self._parse_dockerignore()

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_zip:
            try:
                with zipfile.ZipFile(temp_zip.name, "w", zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk("."):
                        # Convert to relative path
                        rel_root = os.path.relpath(root, ".")
                        if rel_root == ".":
                            rel_root = ""

                        # Filter directories
                        dirs[:] = [
                            d
                            for d in dirs
                            if not self._should_ignore(
                                os.path.join(rel_root, d) if rel_root else d, ignore_patterns, is_dir=True
                            )
                        ]

                        for file in files:
                            file_rel_path = os.path.join(rel_root, file) if rel_root else file

                            # Skip if matches ignore pattern
                            if self._should_ignore(file_rel_path, ignore_patterns, is_dir=False):
                                continue

                            file_path = Path(root) / file
                            zipf.write(file_path, file_rel_path)

                # Create agent-organized S3 key: agentname/source.zip (fixed naming for cache consistency)
                s3_key = f"{agent_name}/source.zip"

                self.s3_client.upload_file(temp_zip.name, bucket_name, s3_key)

                self.logger.info("Uploaded source to S3: %s", s3_key)
                return f"s3://{bucket_name}/{s3_key}"

            finally:
                temp_zip.close()
                os.unlink(temp_zip.name)

    def _normalize_s3_location(self, source_location: str) -> str:
        """Convert s3:// URL to bucket/key format for CodeBuild."""
        return source_location.replace("s3://", "") if source_location.startswith("s3://") else source_location

    def create_codebuild_execution_role(self, account_id: str, ecr_repository_arn: str, agent_name: str) -> str:
        """Get or create CodeBuild execution role using shared role creation logic."""
        return get_or_create_codebuild_execution_role(
            session=self.session,
            logger=self.logger,
            region=self.session.region_name,
            account_id=account_id,
            agent_name=agent_name,
            ecr_repository_arn=ecr_repository_arn,
            source_bucket_name=self.get_source_bucket_name(account_id),
        )

    def create_or_update_project(
        self, agent_name: str, ecr_repository_uri: str, execution_role: str, source_location: str
    ) -> str:
        """Create or update CodeBuild project for ARM64 builds."""
        project_name = f"bedrock-agentcore-{agent_name}-builder"

        buildspec = self._get_arm64_buildspec(ecr_repository_uri)

        # CodeBuild expects S3 location without s3:// prefix (bucket/key format)
        codebuild_source_location = self._normalize_s3_location(source_location)

        project_config = {
            "name": project_name,
            "source": {
                "type": "S3",
                "location": codebuild_source_location,
                "buildspec": buildspec,
            },
            "artifacts": {
                "type": "NO_ARTIFACTS",
            },
            "environment": {
                "type": "ARM_CONTAINER",  # ARM64 images require ARM_CONTAINER environment type
                "image": "aws/codebuild/amazonlinux2-aarch64-standard:3.0",
                "computeType": "BUILD_GENERAL1_MEDIUM",  # 4 vCPUs, 7GB RAM - optimal for I/O workloads
                "privilegedMode": True,  # Required for Docker
            },
            "serviceRole": execution_role,
        }

        try:
            self.client.create_project(**project_config)
            self.logger.info("Created CodeBuild project: %s", project_name)
        except ClientError as e:
            if e.response["Error"]["Code"] == "ResourceAlreadyExistsException":
                self.client.update_project(**project_config)
                self.logger.info("Updated CodeBuild project: %s", project_name)
            else:
                raise

        return project_name

    def start_build(self, project_name: str, source_location: str) -> str:
        """Start a CodeBuild build."""
        # CodeBuild expects S3 location without s3:// prefix (bucket/key format)
        codebuild_source_location = self._normalize_s3_location(source_location)

        response = self.client.start_build(
            projectName=project_name,
            sourceLocationOverride=codebuild_source_location,
        )

        return response["build"]["id"]

    def wait_for_completion(self, build_id: str, timeout: int = 900):
        """Wait for CodeBuild to complete with detailed phase tracking."""
        self.logger.info("Starting CodeBuild monitoring...")

        # Phase tracking variables
        current_phase = None
        phase_start_time = None
        build_start_time = time.time()

        while time.time() - build_start_time < timeout:
            response = self.client.batch_get_builds(ids=[build_id])
            build = response["builds"][0]
            status = build["buildStatus"]
            build_phase = build.get("currentPhase", "UNKNOWN")

            # Track phase changes
            if build_phase != current_phase:
                # Log previous phase completion (if any)
                if current_phase and phase_start_time:
                    phase_duration = time.time() - phase_start_time
                    self.logger.info("✅ %s completed in %.1fs", current_phase, phase_duration)

                # Log new phase start
                current_phase = build_phase
                phase_start_time = time.time()
                total_duration = phase_start_time - build_start_time
                self.logger.info("🔄 %s started (total: %.0fs)", current_phase, total_duration)

            # Check for completion
            if status == "SUCCEEDED":
                # Log final phase completion
                if current_phase and phase_start_time:
                    phase_duration = time.time() - phase_start_time
                    self.logger.info("✅ %s completed in %.1fs", current_phase, phase_duration)

                total_duration = time.time() - build_start_time
                minutes, seconds = divmod(int(total_duration), 60)
                self.logger.info("🎉 CodeBuild completed successfully in %dm %ds", minutes, seconds)
                return

            elif status in ["FAILED", "FAULT", "STOPPED", "TIMED_OUT"]:
                # Log failure with phase info
                if current_phase:
                    self.logger.error("❌ Build failed during %s phase", current_phase)
                raise RuntimeError(f"CodeBuild failed with status: {status}")

            time.sleep(1)

        total_duration = time.time() - build_start_time
        minutes, seconds = divmod(int(total_duration), 60)
        raise TimeoutError(f"CodeBuild timed out after {minutes}m {seconds}s (current phase: {current_phase})")

    def _get_arm64_buildspec(self, ecr_repository_uri: str) -> str:
        """Get optimized buildspec with parallel ECR authentication."""
        return f"""
version: 0.2
phases:
  build:
    commands:
      - echo "Starting parallel Docker build and ECR authentication..."
      - |
        docker build -t bedrock-agentcore-arm64 . &
        BUILD_PID=$!
        aws ecr get-login-password --region $AWS_DEFAULT_REGION | \\
        docker login --username AWS --password-stdin {ecr_repository_uri} &
        AUTH_PID=$!
        echo "Waiting for Docker build to complete..."
        wait $BUILD_PID
        if [ $? -ne 0 ]; then
          echo "Docker build failed"
          exit 1
        fi
        echo "Waiting for ECR authentication to complete..."
        wait $AUTH_PID
        if [ $? -ne 0 ]; then
          echo "ECR authentication failed"
          exit 1
        fi
        echo "Both build and auth completed successfully"
      - echo "Tagging image..."
      - docker tag bedrock-agentcore-arm64:latest {ecr_repository_uri}:latest
  post_build:
    commands:
      - echo "Pushing ARM64 image to ECR..."
      - docker push {ecr_repository_uri}:latest
      - echo "Build completed at $(date)"
"""

    def _parse_dockerignore(self) -> List[str]:
        """Parse .dockerignore file and return list of patterns."""
        dockerignore_path = Path(".dockerignore")
        patterns = []

        if dockerignore_path.exists():
            with open(dockerignore_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)

            self.logger.info("Using .dockerignore with %d patterns", len(patterns))
        else:
            # Default patterns if no .dockerignore
            patterns = [
                ".git",
                "__pycache__",
                "*.pyc",
                ".DS_Store",
                "node_modules",
                ".venv",
                "venv",
                "*.egg-info",
                ".bedrock_agentcore.yaml",  # Always exclude config
            ]
            self.logger.info("No .dockerignore found, using default exclude patterns")

        return patterns

    def _should_ignore(self, path: str, patterns: List[str], is_dir: bool = False) -> bool:
        """Check if path should be ignored based on dockerignore patterns."""
        # Normalize path
        if path.startswith("./"):
            path = path[2:]

        should_ignore = False  # Default state: don't ignore

        for pattern in patterns:
            # Handle negation patterns
            if pattern.startswith("!"):
                if self._matches_pattern(path, pattern[1:], is_dir):
                    should_ignore = False  # Negation pattern: don't ignore
            else:
                # Regular ignore patterns
                if self._matches_pattern(path, pattern, is_dir):
                    should_ignore = True  # Regular pattern: ignore

        return should_ignore

    def _matches_pattern(self, path: str, pattern: str, is_dir: bool) -> bool:
        """Check if path matches a dockerignore pattern."""
        # Directory-specific patterns
        if pattern.endswith("/"):
            if not is_dir:
                return False
            pattern = pattern[:-1]

        # Exact match
        if path == pattern:
            return True

        # Glob pattern match
        if fnmatch.fnmatch(path, pattern):
            return True

        # Directory prefix match
        if is_dir and pattern in path.split("/"):
            return True

        # File in ignored directory
        if not is_dir and any(fnmatch.fnmatch(part, pattern) for part in path.split("/")):
            return True

        return False
