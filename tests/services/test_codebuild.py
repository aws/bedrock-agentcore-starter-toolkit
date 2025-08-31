"""Tests for Bedrock AgentCore CodeBuild service integration."""

import json
from unittest.mock import Mock, mock_open, patch

import pytest
from botocore.exceptions import ClientError

from bedrock_agentcore_starter_toolkit.services.codebuild import CodeBuildService


class TestCodeBuildService:
    """Test CodeBuild service functionality."""

    @pytest.fixture
    def mock_session(self):
        """Mock boto3 session."""
        session = Mock()
        session.region_name = "us-west-2"
        return session

    @pytest.fixture
    def mock_clients(self, mock_session):
        """Mock AWS service clients."""
        clients = {
            "codebuild": Mock(),
            "s3": Mock(),
            "iam": Mock(),
            "sts": Mock(),
        }

        # Configure STS mock
        clients["sts"].get_caller_identity.return_value = {"Account": "123456789012"}

        # Configure S3 mock
        clients["s3"].head_bucket.side_effect = ClientError({"Error": {"Code": "404"}}, "HeadBucket")
        clients["s3"].create_bucket.return_value = {}
        clients["s3"].put_bucket_lifecycle_configuration.return_value = {}
        clients["s3"].upload_file.return_value = {}

        # Configure IAM mock
        clients["iam"].create_role.return_value = {}
        clients["iam"].put_role_policy.return_value = {}

        # Configure CodeBuild mock
        clients["codebuild"].create_project.return_value = {}
        clients["codebuild"].start_build.return_value = {"build": {"id": "test-build-id"}}
        clients["codebuild"].batch_get_builds.return_value = {
            "builds": [{"buildStatus": "SUCCEEDED", "currentPhase": "COMPLETED"}]
        }

        def client_factory(service_name):
            return clients[service_name]

        mock_session.client = client_factory
        return clients

    @pytest.fixture
    def codebuild_service(self, mock_session, mock_clients):
        """Create CodeBuildService instance with mocked dependencies."""
        return CodeBuildService(mock_session)

    def test_init(self, mock_session):
        """Test CodeBuildService initialization."""
        service = CodeBuildService(mock_session)

        assert service.session == mock_session
        assert service.client == mock_session.client("codebuild")
        assert service.s3_client == mock_session.client("s3")
        assert service.iam_client == mock_session.client("iam")
        assert service.source_bucket is None

    def test_get_source_bucket_name(self, codebuild_service):
        """Test S3 bucket name generation."""
        bucket_name = codebuild_service.get_source_bucket_name("123456789012")

        expected = "bedrock-agentcore-codebuild-sources-123456789012-us-west-2"
        assert bucket_name == expected

    def test_ensure_source_bucket_create_new(self, codebuild_service, mock_clients):
        """Test creating new S3 bucket."""
        bucket_name = codebuild_service.ensure_source_bucket("123456789012")

        expected = "bedrock-agentcore-codebuild-sources-123456789012-us-west-2"
        assert bucket_name == expected

        # Verify S3 operations
        mock_clients["s3"].head_bucket.assert_called_once_with(Bucket=expected)
        mock_clients["s3"].create_bucket.assert_called_once_with(
            Bucket=expected, CreateBucketConfiguration={"LocationConstraint": "us-west-2"}
        )
        mock_clients["s3"].put_bucket_lifecycle_configuration.assert_called_once()

    def test_ensure_source_bucket_existing(self, codebuild_service, mock_clients):
        """Test using existing S3 bucket."""
        # Mock existing bucket
        mock_clients["s3"].head_bucket.side_effect = None
        mock_clients["s3"].head_bucket.return_value = {}

        bucket_name = codebuild_service.ensure_source_bucket("123456789012")

        expected = "bedrock-agentcore-codebuild-sources-123456789012-us-west-2"
        assert bucket_name == expected

        # Should not create bucket
        mock_clients["s3"].create_bucket.assert_not_called()

    def test_ensure_source_bucket_us_east_1(self, mock_session, mock_clients):
        """Test bucket creation in us-east-1 region."""
        mock_session.region_name = "us-east-1"
        service = CodeBuildService(mock_session)

        service.ensure_source_bucket("123456789012")

        # Should not specify LocationConstraint for us-east-1
        mock_clients["s3"].create_bucket.assert_called_once_with(
            Bucket="bedrock-agentcore-codebuild-sources-123456789012-us-east-1"
        )

    @patch("os.walk")
    @patch("zipfile.ZipFile")
    @patch("tempfile.NamedTemporaryFile")
    @patch("os.unlink")
    def test_upload_source_success(
        self, mock_unlink, mock_tempfile, mock_zipfile, mock_walk, codebuild_service, mock_clients
    ):
        """Test successful source upload."""
        # Mock file system
        mock_walk.return_value = [(".", ["subdir"], ["file1.py", "file2.txt"]), ("./subdir", [], ["file3.py"])]

        # Mock temp file
        mock_temp = Mock()
        mock_temp.name = "/tmp/test.zip"
        mock_tempfile.return_value.__enter__.return_value = mock_temp

        # Mock zipfile
        mock_zip = Mock()
        mock_zipfile.return_value.__enter__.return_value = mock_zip

        # Test with fixed source.zip naming (no timestamp needed)
        result = codebuild_service.upload_source("test-agent")

        expected_key = "test-agent/source.zip"
        expected_s3_url = f"s3://bedrock-agentcore-codebuild-sources-123456789012-us-west-2/{expected_key}"

        assert result == expected_s3_url
        mock_clients["s3"].upload_file.assert_called_once()
        mock_unlink.assert_called_once_with("/tmp/test.zip")

    def test_normalize_s3_location(self, codebuild_service):
        """Test S3 location normalization."""
        # S3 URL format
        s3_url = "s3://bucket/key"
        result = codebuild_service._normalize_s3_location(s3_url)
        assert result == "bucket/key"

        # Already normalized format
        normalized = "bucket/key"
        result = codebuild_service._normalize_s3_location(normalized)
        assert result == "bucket/key"

    def test_create_codebuild_execution_role_new(self, codebuild_service, mock_clients):
        """Test creating new IAM role when none exists."""
        ecr_arn = "arn:aws:ecr:us-west-2:123456789012:repository/test-repo"

        # Mock role doesn't exist (NoSuchEntity exception)
        mock_clients["iam"].get_role.side_effect = ClientError({"Error": {"Code": "NoSuchEntity"}}, "GetRole")

        # Mock the create_role response properly
        mock_clients["iam"].create_role.return_value = {
            "Role": {"Arn": "arn:aws:iam::123456789012:role/AmazonBedrockAgentCoreSDKCodeBuild-us-west-2-test123456"}
        }

        with patch("time.sleep"):  # Skip sleep in tests
            role_arn = codebuild_service.create_codebuild_execution_role("123456789012", ecr_arn, "test")

        # Role ARN should follow new naming pattern: AmazonBedrockAgentCoreSDKCodeBuild-{region}-{deterministic}
        assert role_arn.startswith("arn:aws:iam::123456789012:role/AmazonBedrockAgentCoreSDKCodeBuild-us-west-2-")

        # Verify IAM operations - should check for existence first, then create
        mock_clients["iam"].get_role.assert_called_once()
        mock_clients["iam"].create_role.assert_called_once()
        mock_clients["iam"].put_role_policy.assert_called_once()

    def test_create_codebuild_execution_role_existing(self, codebuild_service, mock_clients):
        """Test reusing existing IAM role."""
        ecr_arn = "arn:aws:ecr:us-west-2:123456789012:repository/test-repo"

        # Mock role already exists
        mock_clients["iam"].get_role.return_value = {
            "Role": {"Arn": "arn:aws:iam::123456789012:role/AmazonBedrockAgentCoreSDKCodeBuild-us-west-2-existing123"}
        }

        with patch("time.sleep"):  # Skip sleep in tests
            role_arn = codebuild_service.create_codebuild_execution_role("123456789012", ecr_arn, "test")

        # Should return the existing role ARN
        assert role_arn == "arn:aws:iam::123456789012:role/AmazonBedrockAgentCoreSDKCodeBuild-us-west-2-existing123"

        # Verify that get_role was called but create_role was NOT called
        mock_clients["iam"].get_role.assert_called_once()
        mock_clients["iam"].create_role.assert_not_called()
        mock_clients["iam"].put_role_policy.assert_not_called()

    def test_create_or_update_project_new(self, codebuild_service, mock_clients):
        """Test creating new CodeBuild project."""
        project_name = codebuild_service.create_or_update_project(
            "test-agent",
            "123456.dkr.ecr.us-west-2.amazonaws.com/test-repo",
            "arn:aws:iam::123456:role/test-role",
            "s3://bucket/source.zip",
        )

        assert project_name == "bedrock-agentcore-test-agent-builder"
        mock_clients["codebuild"].create_project.assert_called_once()

    def test_create_or_update_project_existing(self, codebuild_service, mock_clients):
        """Test updating existing CodeBuild project."""
        # Mock project already exists
        mock_clients["codebuild"].create_project.side_effect = ClientError(
            {"Error": {"Code": "ResourceAlreadyExistsException"}}, "CreateProject"
        )
        mock_clients["codebuild"].update_project.return_value = {}

        project_name = codebuild_service.create_or_update_project(
            "test-agent",
            "123456.dkr.ecr.us-west-2.amazonaws.com/test-repo",
            "arn:aws:iam::123456:role/test-role",
            "s3://bucket/source.zip",
        )

        assert project_name == "bedrock-agentcore-test-agent-builder"
        mock_clients["codebuild"].update_project.assert_called_once()

    def test_start_build(self, codebuild_service, mock_clients):
        """Test starting CodeBuild build."""
        build_id = codebuild_service.start_build("test-project", "s3://bucket/source.zip")

        assert build_id == "test-build-id"
        mock_clients["codebuild"].start_build.assert_called_once_with(
            projectName="test-project", sourceLocationOverride="bucket/source.zip"
        )

    def test_wait_for_completion_success(self, codebuild_service, mock_clients):
        """Test successful build completion."""
        # Mock build progression
        build_responses = [
            {"builds": [{"buildStatus": "IN_PROGRESS", "currentPhase": "PRE_BUILD"}]},
            {"builds": [{"buildStatus": "IN_PROGRESS", "currentPhase": "BUILD"}]},
            {"builds": [{"buildStatus": "SUCCEEDED", "currentPhase": "COMPLETED"}]},
        ]
        mock_clients["codebuild"].batch_get_builds.side_effect = build_responses

        with patch("bedrock_agentcore_starter_toolkit.services.codebuild.time.sleep"):  # Speed up test
            codebuild_service.wait_for_completion("test-build-id", timeout=10)

        assert mock_clients["codebuild"].batch_get_builds.call_count == 3

    def test_wait_for_completion_failure(self, codebuild_service, mock_clients):
        """Test build failure handling."""
        mock_clients["codebuild"].batch_get_builds.return_value = {
            "builds": [{"buildStatus": "FAILED", "currentPhase": "BUILD"}]
        }

        with pytest.raises(RuntimeError, match="CodeBuild failed with status: FAILED"):
            codebuild_service.wait_for_completion("test-build-id")

    def test_wait_for_completion_timeout(self, codebuild_service, mock_clients):
        """Test build timeout handling."""
        mock_clients["codebuild"].batch_get_builds.return_value = {
            "builds": [{"buildStatus": "IN_PROGRESS", "currentPhase": "BUILD"}]
        }

        with patch("bedrock_agentcore_starter_toolkit.services.codebuild.time.sleep"):
            with pytest.raises(TimeoutError, match="CodeBuild timed out"):
                codebuild_service.wait_for_completion("test-build-id", timeout=1)

    def test_get_arm64_buildspec(self, codebuild_service):
        """Test ARM64 buildspec generation - native build with parallel ECR auth."""
        buildspec = codebuild_service._get_arm64_buildspec("test-ecr-uri")

        assert "version: 0.2" in buildspec
        assert "test-ecr-uri" in buildspec

        # Verify native Docker build (no buildx)
        assert "docker build -t bedrock-agentcore-arm64 ." in buildspec
        assert "docker buildx build" not in buildspec
        assert "linux/arm64" not in buildspec

        # Verify parallel operations with multi-line shell block
        assert "Starting parallel Docker build and ECR authentication..." in buildspec
        assert "- |" in buildspec  # Multi-line block syntax
        assert "docker build -t bedrock-agentcore-arm64 . &" in buildspec
        assert "BUILD_PID=$!" in buildspec
        assert "aws ecr get-login-password" in buildspec
        assert "AUTH_PID=$!" in buildspec

        # Verify explicit error handling
        assert "wait $BUILD_PID" in buildspec
        assert "if [ $? -ne 0 ]; then" in buildspec
        assert "Docker build failed" in buildspec
        assert "wait $AUTH_PID" in buildspec
        assert "ECR authentication failed" in buildspec
        assert "Both build and auth completed successfully" in buildspec

        # Verify final steps
        assert "Tagging image..." in buildspec
        assert "docker tag bedrock-agentcore-arm64:latest" in buildspec

    def test_parse_dockerignore_existing_file(self, codebuild_service):
        """Test parsing existing .dockerignore file."""
        dockerignore_content = """
# Comment
node_modules
*.pyc
.git
"""

        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=dockerignore_content)):
                patterns = codebuild_service._parse_dockerignore()

        expected = ["node_modules", "*.pyc", ".git"]
        assert patterns == expected

    def test_parse_dockerignore_no_file(self, codebuild_service):
        """Test default patterns when no .dockerignore exists."""
        with patch("pathlib.Path.exists", return_value=False):
            patterns = codebuild_service._parse_dockerignore()

        assert ".git" in patterns
        assert "__pycache__" in patterns
        assert "*.pyc" in patterns
        assert ".bedrock_agentcore.yaml" in patterns

    def test_should_ignore_basic_patterns(self, codebuild_service):
        """Test basic ignore pattern matching."""
        patterns = ["*.pyc", "node_modules", ".git"]

        # Should ignore
        assert codebuild_service._should_ignore("test.pyc", patterns, False)
        assert codebuild_service._should_ignore("node_modules", patterns, True)
        assert codebuild_service._should_ignore(".git", patterns, True)

        # Should not ignore
        assert not codebuild_service._should_ignore("test.py", patterns, False)
        assert not codebuild_service._should_ignore("src", patterns, True)

    def test_should_ignore_negation_patterns(self, codebuild_service):
        """Test negation pattern handling."""
        patterns = ["*.log", "!important.log"]

        # Should ignore regular log files
        assert codebuild_service._should_ignore("debug.log", patterns, False)

        # Should NOT ignore important.log due to negation pattern (FIXED!)
        assert not codebuild_service._should_ignore("important.log", patterns, False)

        # Both pattern orders should work correctly
        patterns_negation_first = ["!important.log", "*.log"]
        assert codebuild_service._should_ignore("important.log", patterns_negation_first, False)

    def test_negation_patterns_multiple(self, codebuild_service):
        """Test multiple negation patterns."""
        patterns = ["*.log", "!important.log", "!critical.log", "temp.log"]

        assert codebuild_service._should_ignore("debug.log", patterns, False)
        assert not codebuild_service._should_ignore("important.log", patterns, False)
        assert not codebuild_service._should_ignore("critical.log", patterns, False)
        assert codebuild_service._should_ignore("temp.log", patterns, False)  # Re-ignored

    def test_negation_patterns_directories(self, codebuild_service):
        """Test negation patterns with directories."""
        patterns = ["node_modules/", "!node_modules/important/"]

        assert codebuild_service._should_ignore("node_modules", patterns, True)
        assert not codebuild_service._should_ignore("node_modules/important", patterns, True)

    def test_negation_patterns_complex_precedence(self, codebuild_service):
        """Test complex pattern precedence."""
        patterns = ["*", "!*.py", "test.*", "!test.py"]

        # Everything ignored, except .py files
        assert codebuild_service._should_ignore("file.txt", patterns, False)
        assert not codebuild_service._should_ignore("script.py", patterns, False)

        # test.* re-ignored, but test.py negated again
        assert codebuild_service._should_ignore("test.txt", patterns, False)
        assert not codebuild_service._should_ignore("test.py", patterns, False)

    def test_source_upload_with_negation_patterns(self, codebuild_service, mock_clients):
        """Test source upload with negation patterns in .dockerignore."""
        with (
            patch("os.walk") as mock_walk,
            patch("zipfile.ZipFile") as mock_zipfile,
            patch("tempfile.NamedTemporaryFile") as mock_tempfile,
            patch("os.unlink") as mock_unlink,
            patch.object(codebuild_service, "_parse_dockerignore") as mock_parse,
        ):
            # Mock file system with files to test negation patterns
            mock_walk.return_value = [(".", [], ["debug.log", "important.log", "temp.tmp", "keep.tmp", "code.py"])]

            # Mock dockerignore with negation patterns
            mock_parse.return_value = ["*.log", "!important.log", "*.tmp", "!keep.tmp"]

            # Mock temp file and zipfile
            mock_temp = Mock()
            mock_temp.name = "/tmp/test.zip"
            mock_tempfile.return_value.__enter__.return_value = mock_temp

            mock_zip = Mock()
            mock_zipfile.return_value.__enter__.return_value = mock_zip

            # Test with fixed source.zip naming
            codebuild_service.upload_source("test-agent")

            # Verify correct files were included/excluded
            zip_calls = mock_zip.write.call_args_list
            written_files = [call[0][1] for call in zip_calls]

            assert "important.log" in written_files  # Negated, should be included
            assert "keep.tmp" in written_files  # Negated, should be included
            assert "code.py" in written_files  # Not matched, should be included
            assert "debug.log" not in written_files  # Ignored
            assert "temp.tmp" not in written_files  # Ignored

            # Verify cleanup was called
            mock_unlink.assert_called_once_with("/tmp/test.zip")

    def test_matches_pattern_exact_match(self, codebuild_service):
        """Test exact pattern matching."""
        assert codebuild_service._matches_pattern("test.py", "test.py", False)
        assert not codebuild_service._matches_pattern("test.pyc", "test.py", False)

    def test_matches_pattern_glob(self, codebuild_service):
        """Test glob pattern matching."""
        assert codebuild_service._matches_pattern("test.pyc", "*.pyc", False)
        assert codebuild_service._matches_pattern("src/test.pyc", "*.pyc", False)
        assert not codebuild_service._matches_pattern("test.py", "*.pyc", False)

    def test_matches_pattern_directory(self, codebuild_service):
        """Test directory pattern matching."""
        # Directory-specific pattern
        assert codebuild_service._matches_pattern("node_modules", "node_modules/", True)
        assert not codebuild_service._matches_pattern("node_modules.txt", "node_modules/", False)

    def test_source_upload_with_dockerignore(self, codebuild_service, mock_clients):
        """Test source upload respecting .dockerignore patterns."""
        with (
            patch("os.walk") as mock_walk,
            patch("zipfile.ZipFile") as mock_zipfile,
            patch("tempfile.NamedTemporaryFile") as mock_tempfile,
            patch("os.unlink") as mock_unlink,
            patch.object(codebuild_service, "_parse_dockerignore") as mock_parse,
        ):
            # Mock file system with files to ignore
            mock_walk.return_value = [(".", [], ["test.py", "test.pyc", ".git", "README.md"])]

            # Mock dockerignore patterns
            mock_parse.return_value = ["*.pyc", ".git"]

            # Mock temp file and zipfile
            mock_temp = Mock()
            mock_temp.name = "/tmp/test.zip"
            mock_tempfile.return_value.__enter__.return_value = mock_temp

            mock_zip = Mock()
            mock_zipfile.return_value.__enter__.return_value = mock_zip

            # Test with fixed source.zip naming
            codebuild_service.upload_source("test-agent")

            # Verify only non-ignored files were added to zip
            zip_calls = mock_zip.write.call_args_list
            written_files = [call[0][1] for call in zip_calls]  # Second arg is the archive name

            assert "test.py" in written_files
            assert "README.md" in written_files
            assert "test.pyc" not in written_files
            assert ".git" not in written_files

            # Verify cleanup was called
            mock_unlink.assert_called_once_with("/tmp/test.zip")

    def test_project_config_arm64_settings(self, codebuild_service, mock_clients):
        """Test CodeBuild project uses correct ARM64 settings."""
        codebuild_service.create_or_update_project(
            "test-agent",
            "123456.dkr.ecr.us-west-2.amazonaws.com/test-repo",
            "arn:aws:iam::123456:role/test-role",
            "s3://bucket/source.zip",
        )

        # Verify project config
        call_args = mock_clients["codebuild"].create_project.call_args[1]

        assert call_args["environment"]["type"] == "ARM_CONTAINER"
        assert call_args["environment"]["image"] == "aws/codebuild/amazonlinux2-aarch64-standard:3.0"
        assert call_args["environment"]["computeType"] == "BUILD_GENERAL1_MEDIUM"
        assert call_args["environment"]["privilegedMode"] is True

    def test_iam_role_permissions(self, codebuild_service, mock_clients):
        """Test IAM role has correct permissions."""
        ecr_arn = "arn:aws:ecr:us-west-2:123456789012:repository/test-repo"

        # Mock role doesn't exist (NoSuchEntity exception)
        mock_clients["iam"].get_role.side_effect = ClientError({"Error": {"Code": "NoSuchEntity"}}, "GetRole")

        # Mock the create_role response properly
        mock_clients["iam"].create_role.return_value = {
            "Role": {"Arn": "arn:aws:iam::123456789012:role/AmazonBedrockAgentCoreSDKCodeBuild-us-west-2-test123456"}
        }

        with patch("time.sleep"):
            codebuild_service.create_codebuild_execution_role("123456789012", ecr_arn, "test")

        # Check policy document
        policy_call = mock_clients["iam"].put_role_policy.call_args
        policy_doc = json.loads(policy_call[1]["PolicyDocument"])

        # Verify ECR permissions
        ecr_statement = next(
            stmt for stmt in policy_doc["Statement"] if "ecr:BatchCheckLayerAvailability" in stmt["Action"]
        )
        assert ecr_arn in ecr_statement["Resource"]

        # Verify S3 permissions
        s3_statement = next(stmt for stmt in policy_doc["Statement"] if "s3:GetObject" in stmt["Action"])
        assert "bedrock-agentcore-codebuild-sources-123456789012-us-west-2" in s3_statement["Resource"]
