from unittest.mock import patch


class TestCLICommon:
    def test_prompt_with_default_with_input(self):
        """Test _prompt_with_default with user input."""
        from bedrock_agentcore_starter_toolkit.cli.common import _prompt_with_default

        with patch("bedrock_agentcore_starter_toolkit.cli.common.prompt", return_value="user_input"):
            result = _prompt_with_default("Enter value", "default_value")
            assert result == "user_input"

    def test_prompt_with_default_empty_input(self):
        """Test _prompt_with_default with empty input."""
        from bedrock_agentcore_starter_toolkit.cli.common import _prompt_with_default

        with patch("bedrock_agentcore_starter_toolkit.cli.common.prompt", return_value=""):
            result = _prompt_with_default("Enter value", "default_value")
            assert result == "default_value"
