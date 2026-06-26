"""Tests for the create completion message and its trailing recommendation."""

from pathlib import Path
from unittest.mock import patch

from bedrock_agentcore_starter_toolkit.create.types import ProjectContext
from bedrock_agentcore_starter_toolkit.create.util import console_print


def _flat(text: str) -> str:
    """Collapse all whitespace so width-based line wrapping doesn't break asserts."""
    return " ".join(text.split())


def _ctx(**overrides) -> ProjectContext:
    base = dict(
        name="myAgent",
        output_dir=Path("myAgent"),
        src_dir=Path("myAgent/src"),
        entrypoint_path=Path("myAgent/src/main.py"),
        sdk_provider="Strands",
        iac_provider=None,
        model_provider="Bedrock",
        template_dir_selection="runtime_only",
        runtime_protocol="HTTP",
        deployment_type="direct_code_deploy",
        python_dependencies=[],
    )
    base.update(overrides)
    return ProjectContext(**base)


class TestEmitCreateCompletedMessage:
    @patch("bedrock_agentcore_starter_toolkit.create.util.console_print.print_recommendation")
    @patch("bedrock_agentcore_starter_toolkit.create.util.console_print._emit_next_steps")
    def test_recommendation_printed_after_next_steps(self, mock_next_steps, mock_reco):
        """Recommendation must be the LAST thing printed, after the next-steps panel."""
        call_order = []
        mock_next_steps.side_effect = lambda ctx: call_order.append("next_steps")
        mock_reco.side_effect = lambda console: call_order.append("recommendation")

        console_print.emit_create_completed_message(_ctx())

        assert call_order == ["next_steps", "recommendation"]

    @patch("bedrock_agentcore_starter_toolkit.create.util.console_print.print_recommendation")
    def test_basic_runtime_panel_then_recommendation(self, mock_reco, capsys):
        console_print.emit_create_completed_message(_ctx(iac_provider=None))
        out = _flat(capsys.readouterr().out)
        assert "You're ready to go!" in out
        assert "agentcore deploy" in out
        mock_reco.assert_called_once()

    @patch("bedrock_agentcore_starter_toolkit.create.util.console_print.print_recommendation")
    def test_production_panel_then_recommendation(self, mock_reco, capsys):
        console_print.emit_create_completed_message(
            _ctx(iac_provider="CDK", deployment_type="container", agent_name="myAgent")
        )
        out = _flat(capsys.readouterr().out)
        assert "You're ready to go!" in out
        assert "Deploy your project" in out
        mock_reco.assert_called_once()
