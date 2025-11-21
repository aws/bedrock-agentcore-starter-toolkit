"""Unit tests for dotenv utility module."""

from bedrock_agentcore_starter_toolkit.create.constants import ModelProvider
from bedrock_agentcore_starter_toolkit.create.util.dotenv import _write_env_file_directly


class TestWriteEnvFileDirectly:
    """Tests for _write_env_file_directly function."""

    def test_creates_env_file_for_openai(self, tmp_path):
        """Test that .env file is created for OpenAI provider."""
        _write_env_file_directly(tmp_path, ModelProvider.OpenAI, "test-api-key")

        env_path = tmp_path / ".env"
        assert env_path.exists()
        content = env_path.read_text()
        assert "OPENAI_API_KEY=test-api-key" in content

    def test_creates_env_file_for_anthropic(self, tmp_path):
        """Test that .env file is created for Anthropic provider."""
        _write_env_file_directly(tmp_path, ModelProvider.Anthropic, "anthropic-key")

        env_path = tmp_path / ".env"
        assert env_path.exists()
        content = env_path.read_text()
        assert "ANTHROPIC_API_KEY=anthropic-key" in content

    def test_creates_env_file_for_gemini(self, tmp_path):
        """Test that .env file is created for Gemini provider."""
        _write_env_file_directly(tmp_path, ModelProvider.Gemini, "gemini-key")

        env_path = tmp_path / ".env"
        assert env_path.exists()
        content = env_path.read_text()
        assert "GEMINI_API_KEY=gemini-key" in content

    def test_skips_env_file_for_bedrock(self, tmp_path):
        """Test that .env file is NOT created for Bedrock provider."""
        _write_env_file_directly(tmp_path, ModelProvider.Bedrock, None)

        env_path = tmp_path / ".env"
        assert not env_path.exists()

    def test_empty_api_key_writes_empty_string(self, tmp_path):
        """Test that empty API key writes empty quoted string."""
        _write_env_file_directly(tmp_path, ModelProvider.OpenAI, None)

        env_path = tmp_path / ".env"
        assert env_path.exists()
        content = env_path.read_text()
        assert 'OPENAI_API_KEY=""' in content

    def test_empty_string_api_key_writes_empty_string(self, tmp_path):
        """Test that empty string API key writes empty quoted string."""
        _write_env_file_directly(tmp_path, ModelProvider.OpenAI, "")

        env_path = tmp_path / ".env"
        content = env_path.read_text()
        assert 'OPENAI_API_KEY=""' in content

    def test_env_file_has_newline(self, tmp_path):
        """Test that .env file ends with newline."""
        _write_env_file_directly(tmp_path, ModelProvider.OpenAI, "test-key")

        env_path = tmp_path / ".env"
        content = env_path.read_text()
        assert content.endswith("\n")

    def test_overwrites_existing_env_file(self, tmp_path):
        """Test that existing .env file is overwritten."""
        env_path = tmp_path / ".env"
        env_path.write_text("OLD_KEY=old-value\n")

        _write_env_file_directly(tmp_path, ModelProvider.OpenAI, "new-key")

        content = env_path.read_text()
        assert "OLD_KEY" not in content
        assert "OPENAI_API_KEY=new-key" in content

    def test_api_key_case_sensitivity(self, tmp_path):
        """Test that model provider name is uppercased in env var name."""
        _write_env_file_directly(tmp_path, "openai", "test-key")

        env_path = tmp_path / ".env"
        content = env_path.read_text()
        assert "OPENAI_API_KEY=test-key" in content
