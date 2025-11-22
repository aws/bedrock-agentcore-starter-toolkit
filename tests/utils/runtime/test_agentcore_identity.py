"""Tests for agentcore_identity.py - API key loading utilities."""

from unittest.mock import Mock

from bedrock_agentcore_starter_toolkit.utils.runtime.agentcore_identity import (
    _load_api_key_from_env_if_configured,
    _parse_env_file,
)


class TestParseEnvFile:
    """Test _parse_env_file function."""

    def test_parse_basic_env_file(self, tmp_path):
        """Test parsing a basic .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret123\nDEBUG=true")

        result = _parse_env_file(env_file)

        assert result == {"API_KEY": "secret123", "DEBUG": "true"}

    def test_parse_env_file_with_comments(self, tmp_path):
        """Test parsing .env file with comments."""
        env_file = tmp_path / ".env"
        env_file.write_text("# This is a comment\nAPI_KEY=secret123\n# Another comment\nDEBUG=true")

        result = _parse_env_file(env_file)

        assert result == {"API_KEY": "secret123", "DEBUG": "true"}

    def test_parse_env_file_with_empty_lines(self, tmp_path):
        """Test parsing .env file with empty lines."""
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret123\n\n\nDEBUG=true\n\n")

        result = _parse_env_file(env_file)

        assert result == {"API_KEY": "secret123", "DEBUG": "true"}

    def test_parse_env_file_with_double_quotes(self, tmp_path):
        """Test parsing .env file with double-quoted values."""
        env_file = tmp_path / ".env"
        env_file.write_text('API_KEY="secret123"\nMESSAGE="Hello World"')

        result = _parse_env_file(env_file)

        assert result == {"API_KEY": "secret123", "MESSAGE": "Hello World"}

    def test_parse_env_file_with_single_quotes(self, tmp_path):
        """Test parsing .env file with single-quoted values."""
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY='secret123'\nMESSAGE='Hello World'")

        result = _parse_env_file(env_file)

        assert result == {"API_KEY": "secret123", "MESSAGE": "Hello World"}

    def test_parse_env_file_with_whitespace(self, tmp_path):
        """Test parsing .env file with whitespace around keys and values."""
        env_file = tmp_path / ".env"
        env_file.write_text("  API_KEY  =  secret123  \n  DEBUG  =  true  ")

        result = _parse_env_file(env_file)

        assert result == {"API_KEY": "secret123", "DEBUG": "true"}

    def test_parse_env_file_with_equals_in_value(self, tmp_path):
        """Test parsing .env file with equals sign in value."""
        env_file = tmp_path / ".env"
        env_file.write_text("CONNECTION_STRING=host=localhost;port=5432")

        result = _parse_env_file(env_file)

        assert result == {"CONNECTION_STRING": "host=localhost;port=5432"}

    def test_parse_env_file_empty(self, tmp_path):
        """Test parsing empty .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("")

        result = _parse_env_file(env_file)

        assert result == {}

    def test_parse_env_file_nonexistent(self, tmp_path):
        """Test parsing nonexistent .env file returns empty dict."""
        env_file = tmp_path / ".env"  # File doesn't exist

        result = _parse_env_file(env_file)

        assert result == {}

    def test_parse_env_file_malformed_lines(self, tmp_path):
        """Test parsing .env file with malformed lines (no equals)."""
        env_file = tmp_path / ".env"
        env_file.write_text("API_KEY=secret123\nINVALID_LINE\nDEBUG=true")

        result = _parse_env_file(env_file)

        # Invalid line should be skipped
        assert result == {"API_KEY": "secret123", "DEBUG": "true"}


class TestLoadApiKeyFromEnvIfConfigured:
    """Test _load_api_key_from_env_if_configured function."""

    def test_no_api_key_configured(self, tmp_path):
        """Test when agent has no api_key_env_var_name configured."""
        agent_config = Mock()
        agent_config.api_key_env_var_name = None

        result = _load_api_key_from_env_if_configured(agent_config, tmp_path)

        assert result is None

    def test_api_key_configured_no_env_file(self, tmp_path):
        """Test when api_key_env_var_name is configured but no .env file exists."""
        agent_config = Mock()
        agent_config.api_key_env_var_name = "OPENAI_API_KEY"

        result = _load_api_key_from_env_if_configured(agent_config, tmp_path)

        assert result is None

    def test_api_key_loaded_successfully(self, tmp_path):
        """Test successfully loading API key from .env file."""
        # Create .env file
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=sk-test123456")

        agent_config = Mock()
        agent_config.api_key_env_var_name = "OPENAI_API_KEY"

        result = _load_api_key_from_env_if_configured(agent_config, tmp_path)

        assert result == "sk-test123456"

    def test_api_key_not_in_env_file(self, tmp_path):
        """Test when .env file exists but doesn't contain the required key."""
        # Create .env file without the required key
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_KEY=value")

        agent_config = Mock()
        agent_config.api_key_env_var_name = "OPENAI_API_KEY"

        result = _load_api_key_from_env_if_configured(agent_config, tmp_path)

        assert result is None

    def test_api_key_with_quotes(self, tmp_path):
        """Test loading API key that has quotes in .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text('ANTHROPIC_API_KEY="sk-ant-test123"')

        agent_config = Mock()
        agent_config.api_key_env_var_name = "ANTHROPIC_API_KEY"

        result = _load_api_key_from_env_if_configured(agent_config, tmp_path)

        assert result == "sk-ant-test123"

    def test_different_api_key_names(self, tmp_path):
        """Test loading different API key environment variable names."""
        env_file = tmp_path / ".env"
        env_file.write_text("CUSTOM_API_KEY=custom-secret\nGEMINI_API_KEY=gemini-secret")

        # Test custom key
        agent_config = Mock()
        agent_config.api_key_env_var_name = "CUSTOM_API_KEY"
        result = _load_api_key_from_env_if_configured(agent_config, tmp_path)
        assert result == "custom-secret"

        # Test gemini key
        agent_config.api_key_env_var_name = "GEMINI_API_KEY"
        result = _load_api_key_from_env_if_configured(agent_config, tmp_path)
        assert result == "gemini-secret"

    def test_empty_api_key_value(self, tmp_path):
        """Test when API key value is empty in .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("OPENAI_API_KEY=")

        agent_config = Mock()
        agent_config.api_key_env_var_name = "OPENAI_API_KEY"

        result = _load_api_key_from_env_if_configured(agent_config, tmp_path)

        # Empty string is falsy, so should return None
        assert result is None
