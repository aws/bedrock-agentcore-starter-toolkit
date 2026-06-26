"""Tests for the AgentCore CLI migration recommendation and the CLI banner."""

from unittest.mock import MagicMock, patch

import click
from typer.main import get_command
from typer.testing import CliRunner

from bedrock_agentcore_starter_toolkit.cli import recommendation
from bedrock_agentcore_starter_toolkit.cli.cli import app

runner = CliRunner()


def _all_command_paths():
    """Walk the full Click command tree and return every invocable path.

    Discovering paths from the tree (rather than hardcoding) means a newly
    added command is automatically covered — banner coverage can't silently
    regress.
    """
    root = get_command(app)
    paths = []

    def walk(cmd, prefix):
        if isinstance(cmd, click.Group):
            ctx = click.Context(cmd, info_name=prefix[-1] if prefix else None)
            for name in cmd.list_commands(ctx):
                walk(cmd.get_command(ctx, name), prefix + [name])
            if prefix:  # the group itself is invocable (e.g. `agentcore memory`)
                paths.append(list(prefix))
        else:
            paths.append(list(prefix))

    walk(root, [])
    return sorted(paths)


class TestRecommendationModule:
    def test_text_contains_install_uninstall_and_import(self):
        text = recommendation.recommendation_text()
        assert recommendation.INSTALL_CMD in text
        assert recommendation.UNINSTALL_CMD in text
        assert recommendation.IMPORT_CMD in text
        assert recommendation.SUPPRESS_ENV_VAR in text

    def test_text_leads_with_no_longer_supported_headline(self):
        text = recommendation.recommendation_text()
        assert "The Starter Toolkit CLI is no longer supported. Please use the AgentCore CLI" in text
        assert "(@aws/agentcore)" in text

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


# Stable phrase from the banner headline; used as the presence sentinel so
# wording tweaks elsewhere in the message don't break these tests.
BANNER_SENTINEL = "no longer supported"


class TestBannerAcrossCommands:
    """The banner is a top-level callback; it must fire for every command path."""

    def _stderr(self, *args, env=None):
        # Click 8.3+ captures stderr separately by default; banner goes to stderr.
        result = runner.invoke(app, list(args), env=env or {})
        return _flat(result.stderr)

    def test_banner_shown_for_top_level_command_help(self):
        assert BANNER_SENTINEL in self._stderr("dev", "--help")

    def test_banner_shown_for_create_help(self):
        assert BANNER_SENTINEL in self._stderr("create", "--help")

    def test_banner_shown_for_subgroup_help(self):
        for group in ("memory", "gateway", "identity", "obs", "policy", "eval"):
            assert BANNER_SENTINEL in self._stderr(group, "--help"), group

    def test_banner_shown_for_nested_subcommand_help(self):
        assert BANNER_SENTINEL in self._stderr("create", "import", "--help")

    def test_banner_includes_uninstall_command(self):
        assert "pip uninstall bedrock-agentcore-starter-toolkit" in self._stderr("dev", "--help")

    def test_banner_suppressed_by_env_var(self):
        stderr = self._stderr("dev", "--help", env={"AGENTCORE_SUPPRESS_RECOMMENDATION": "1"})
        assert BANNER_SENTINEL not in stderr

    def test_banner_not_shown_for_bare_invocation(self):
        # Bare `agentcore` with no subcommand shows help only; no banner clutter.
        assert BANNER_SENTINEL not in self._stderr()

    def test_banner_fires_on_every_command_path(self):
        """Hermetic coverage: the top banner must fire for EVERY command path.

        Uses --help so each command's body never runs (no AWS, no side effects);
        the banner is a parent-group callback that fires before --help short-circuits.
        """
        missing = []
        for path in _all_command_paths():
            stderr = self._stderr(*path, "--help")
            if BANNER_SENTINEL not in stderr:
                missing.append(" ".join(path))
        assert not missing, f"Banner missing for command paths: {missing}"

    def test_discovers_full_command_tree(self):
        # Guards the discovery helper itself — if this drops near zero, the
        # coverage test above would pass vacuously.
        paths = _all_command_paths()
        assert len(paths) >= 70, f"Expected the full tree (~78 paths), found {len(paths)}"


class TestReEmitOnFloodCommands:
    """High-output commands re-emit the recommendation at the END so it survives
    the output flood that scrolls the top banner away.

    We patch print_recommendation where each command imports it and assert it
    fires on the success path — independent of terminal width or output volume.
    """

    def _config_file(self, tmp_path):
        config_file = tmp_path / ".bedrock_agentcore.yaml"
        config_file.write_text("""default_agent: test-agent
agents:
  test-agent:
    name: test-agent
    entrypoint: test.py
    platform: linux/arm64
    container_runtime: docker
    aws:
      region: us-west-2
      account: "123456789012"
      execution_role: arn:aws:iam::123456789012:role/TestRole
      ecr_repository: null
      ecr_auto_create: true
      network_configuration:
        network_mode: PUBLIC
      observability:
        enabled: true
    bedrock_agentcore:
      agent_id: null
      agent_arn: null
      endpoint_arn: null""")

    def test_deploy_reemits_recommendation_on_success(self, tmp_path, monkeypatch):
        self._config_file(tmp_path)
        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.launch_bedrock_agentcore") as mock_launch,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.print_recommendation") as mock_reco,
            patch("bedrock_agentcore_starter_toolkit.cli.common.ensure_valid_aws_creds", return_value=(True, None)),
        ):
            mock_result = MagicMock()
            mock_result.mode = "cloud"
            mock_result.tag = "bedrock_agentcore-test-agent"
            mock_result.agent_arn = "arn:aws:bedrock_agentcore:us-west-2:123456789012:agent-runtime/test-id"
            mock_result.ecr_uri = "123456789012.dkr.ecr.us-west-2.amazonaws.com/test"
            mock_result.agent_id = None
            mock_launch.return_value = mock_result

            monkeypatch.chdir(tmp_path)
            result = runner.invoke(app, ["deploy"], catch_exceptions=False)

        assert result.exit_code == 0
        mock_reco.assert_called_once()

    def test_deploy_does_not_reemit_on_error(self, tmp_path, monkeypatch):
        self._config_file(tmp_path)
        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.launch_bedrock_agentcore") as mock_launch,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.print_recommendation") as mock_reco,
            patch("bedrock_agentcore_starter_toolkit.cli.common.ensure_valid_aws_creds", return_value=(True, None)),
        ):
            mock_launch.side_effect = ValueError("boom")
            monkeypatch.chdir(tmp_path)
            runner.invoke(app, ["deploy"])

        # Error path raises before the end-of-command re-emit; the top banner
        # is still visible because error output is short.
        mock_reco.assert_not_called()

    def test_import_agent_reemits_recommendation_on_completion(self, tmp_path, monkeypatch):
        # Drive import-agent fully non-interactively to the "Don't run now"
        # completion branch, mocking only the AWS/translation boundary.
        ia = "bedrock_agentcore_starter_toolkit.cli.create.import_agent.commands"
        agents = [{"id": "AGENT123", "name": "MyAgent", "description": "d"}]
        aliases = [{"id": "ALIAS123", "name": "prod", "description": "d"}]

        translator = MagicMock()
        translator.translate_bedrock_to_strands.return_value = {}

        with (
            patch(f"{ia}.print_recommendation") as mock_reco,
            patch(f"{ia}.requires_aws_creds", lambda f: f),
            patch("bedrock_agentcore_starter_toolkit.cli.common.ensure_valid_aws_creds", return_value=(True, None)),
            patch("boto3.Session"),
            patch(f"{ia}.get_clients", return_value=(MagicMock(), MagicMock())),
            patch(f"{ia}.get_agents", return_value=agents),
            patch(f"{ia}.get_agent_aliases", return_value=aliases),
            patch(f"{ia}.auth_and_get_info", return_value=MagicMock()),
            patch(f"{ia}.BedrockStrandsTranslation", return_value=translator),
        ):
            monkeypatch.chdir(tmp_path)
            result = runner.invoke(
                app,
                [
                    "create",
                    "import",
                    "--agent-id",
                    "AGENT123",
                    "--agent-alias-id",
                    "ALIAS123",
                    "--target-platform",
                    "strands",
                    "--region",
                    "us-west-2",
                    "--run-option",
                    "none",
                    "--output-dir",
                    str(tmp_path / "out"),
                ],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, result.output
        mock_reco.assert_called_once()

    def test_configure_reemits_recommendation_on_success(self, tmp_path, monkeypatch):
        agent_file = tmp_path / "test_agent.py"
        agent_file.write_text("from bedrock_agentcore.runtime import BedrockAgentCoreApp\napp = BedrockAgentCoreApp()")
        with (
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.configure_impl") as mock_impl,
            patch("bedrock_agentcore_starter_toolkit.cli.runtime.commands.print_recommendation") as mock_reco,
            patch(
                "bedrock_agentcore_starter_toolkit.cli.common.ensure_valid_aws_creds",
                return_value=(True, None),
            ),
        ):
            monkeypatch.chdir(tmp_path)
            result = runner.invoke(
                app,
                ["configure", "--entrypoint", str(agent_file), "--execution-role", "TestRole", "--non-interactive"],
            )

        assert mock_impl.called
        assert result.exit_code == 0
        mock_reco.assert_called_once()
