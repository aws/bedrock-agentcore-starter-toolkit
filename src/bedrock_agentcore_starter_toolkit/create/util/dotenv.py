"""Utilities for dotenv."""

from pathlib import Path

from ...create.constants import ModelProvider


def _write_env_file_directly(output_dir: Path, model_provider: str, api_key: str | None) -> None:
    """Write .env file with API key for non-Bedrock providers.

    This function handles sensitive data (API keys) outside of the template system
    to prevent accidental exposure through ProjectContext or logging.

    Args:
        output_dir: Directory where .env file should be created
        model_provider: Name of the model provider (e.g., "OpenAI", "Bedrock")
        api_key: API key to write to .env file (None/empty for Bedrock or if not provided)
    """
    # Skip .env creation for Bedrock (uses IAM)
    if model_provider == ModelProvider.Bedrock:
        return

    # Write .env for non-Bedrock providers, with empty string if no key provided
    env_path = output_dir / ".env"
    api_key_value = api_key if api_key else '""'
    env_content = f"{model_provider.upper()}_API_KEY={api_key_value}\n"
    env_path.write_text(env_content)
