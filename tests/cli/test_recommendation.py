"""Tests for the AgentCore CLI migration recommendation and the CLI banner."""

from typer.testing import CliRunner

from bedrock_agentcore_starter_toolkit.cli import recommendation
from bedrock_agentcore_starter_toolkit.cli.cli import app

runner = CliRunner()


class TestRecommendationModule:
    def test_text_contains_install_uninstall_and_import(self):
        text = recommendation.recommendation_text()
        assert recommendation.INSTALL_CMD in text
        assert recommendation.UNINSTALL_CMD in text
        assert recommendation.IMPORT_CMD in text
        assert recommendation.SUPPRESS_ENV_VAR in text

    def test_uninstall_command_targets_the_starter_toolkit(self):
        assert recommendation.UNINSTALL_CMD == "pip uninstall bedrock-agentcore-starter-toolkit"

    def test_not_suppressed_by_default(self, monkeypatch):
        monkeypatch.delenv(recommendation.SUPPRESS_ENV_VAR, raising=False)
        assert recommendation.is_recommendation_suppressed() is False

    def test_suppressed_for_truthy_values(self, monkeypatch):
        for value in ("1", "true", "TRUE", "yes", "Yes"):
            monkeypatch.setenv(recommendation.SUPPRESS_ENV_VAR, value)
            assert recommendation.is_recommendation_suppressed() is True

    def test_not_suppressed_for_other_values(self, monkeypatch):
        for value in ("0", "false", "no", ""):
            monkeypatch.setenv(recommendation.SUPPRESS_ENV_VAR, value)
            assert recommendation.is_recommendation_suppressed() is False

    def test_print_recommendation_respects_suppression(self, monkeypatch):
        printed = []

        class FakeConsole:
            def print(self, *args, **kwargs):
                printed.append(args)

        monkeypatch.setenv(recommendation.SUPPRESS_ENV_VAR, "1")
        recommendation.print_recommendation(FakeConsole())
        assert printed == []

        monkeypatch.setenv(recommendation.SUPPRESS_ENV_VAR, "0")
        recommendation.print_recommendation(FakeConsole())
        assert printed != []


def _flat(text: str) -> str:
    """Collapse all whitespace so width-based line wrapping doesn't break asserts."""
    return " ".join(text.split())


class TestBannerAcrossCommands:
    """The banner is a top-level callback; it must fire for every command path."""

    def _stderr(self, *args, env=None):
        # Click 8.3+ captures stderr separately by default; banner goes to stderr.
        result = runner.invoke(app, list(args), env=env or {})
        return _flat(result.stderr)

    def test_banner_shown_for_top_level_command_help(self):
        assert "now the recommended way" in self._stderr("dev", "--help")

    def test_banner_shown_for_create_help(self):
        assert "now the recommended way" in self._stderr("create", "--help")

    def test_banner_shown_for_subgroup_help(self):
        for group in ("memory", "gateway", "identity", "obs", "policy", "eval"):
            assert "now the recommended way" in self._stderr(group, "--help"), group

    def test_banner_shown_for_nested_subcommand_help(self):
        assert "now the recommended way" in self._stderr("create", "import", "--help")

    def test_banner_includes_uninstall_command(self):
        assert "pip uninstall bedrock-agentcore-starter-toolkit" in self._stderr("dev", "--help")

    def test_banner_suppressed_by_env_var(self):
        stderr = self._stderr("dev", "--help", env={"AGENTCORE_SUPPRESS_RECOMMENDATION": "1"})
        assert "now the recommended way" not in stderr

    def test_banner_not_shown_for_bare_invocation(self):
        # Bare `agentcore` with no subcommand shows help only; no banner clutter.
        assert "now the recommended way" not in self._stderr()
