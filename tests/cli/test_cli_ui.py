"""Unit tests for the CLI UI components."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from bedrock_agentcore_starter_toolkit.cli.cli_ui import (
    OptionState,
    ask_text,
    ask_text_with_validation,
    build_option_fragments,
    intro_animate_once,
    sandwich_text_ui,
    select_one,
    show_invalid_aws_creds,
)


class TestOptionState:
    """Tests for the OptionState logic class."""

    def test_init_and_properties(self):
        """Test initialization and property access."""
        values = [("val1", "Name 1", "Desc 1"), ("val2", "Name 2", None)]
        state = OptionState(values)

        assert state.current == 0
        assert state.selected == "val1"
        assert state.current_value == "val1"
        assert state.finalized is False
        assert state.max_name_len == 6

    def test_empty_init(self):
        """Test initialization with empty list."""
        state = OptionState([])
        assert state.selected is None
        assert state.max_name_len == 0


class TestFragments:
    """Tests for the prompt_toolkit fragment generators."""

    def test_build_option_fragments_normal(self):
        """Test rendering of the option list in normal state."""
        values = [("a", "Alpha", "Description"), ("b", "Beta", None)]
        state = OptionState(values)

        # Cursor is at 0 ("Alpha")
        fragments = build_option_fragments(state)

        # Check first item (selected/cursor)
        # Expected: prefix, bullet, name, desc, newline
        text_content = "".join([f[1] for f in fragments])

        assert "> " in text_content  # Cursor prefix
        assert "● " in text_content  # Selected bullet
        assert "Alpha" in text_content
        assert "- Description" in text_content
        assert "Beta" in text_content

        # Verify styles for selected item
        assert fragments[0] == ("class:cyan", "> ")
        assert fragments[2] == ("class:selected-name", "Alpha")

    def test_build_option_fragments_finalized(self):
        """Test rendering when selection is finalized (collapsed view)."""
        values = [("a", "Alpha", "Desc")]
        state = OptionState(values)
        state.finalized = True
        state.selected = "a"

        fragments = build_option_fragments(state)

        assert len(fragments) == 2
        assert fragments[0] == ("class:selected-name", "a")
        assert fragments[1] == ("", "\n")


class TestInteractiveComponents:
    """Tests for interactive prompt_toolkit applications."""

    @pytest.fixture
    def mock_key_bindings(self):
        """Fixture to mock KeyBindings and capture handlers."""
        with patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.KeyBindings") as mock_kb_cls:
            mock_kb_inst = mock_kb_cls.return_value
            handlers = {}

            def add_side_effect(*keys):
                def decorator(func):
                    for k in keys:
                        handlers[k] = func
                    return func

                return decorator

            mock_kb_inst.add.side_effect = add_side_effect
            mock_kb_inst.captured_handlers = handlers
            yield mock_kb_inst

    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.Application")
    def test_select_one_navigation(self, mock_app_cls, mock_key_bindings):
        """Test keybindings and navigation in select_one."""
        # Setup mock app instance
        mock_app = Mock()
        mock_app_cls.return_value = mock_app
        mock_app.run.return_value = "val2"

        options = ["val1", "val2", "val3"]

        # Capture the real OptionState instance created inside the function
        captured_states = []

        def state_side_effect(*args, **kwargs):
            real_state = OptionState(*args, **kwargs)
            captured_states.append(real_state)
            return real_state

        with patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.OptionState") as mock_state_cls:
            mock_state_cls.side_effect = state_side_effect

            result = select_one("Choose", options)

            assert result == "val2"

            # Retrieve captured state
            assert len(captured_states) == 1
            state_instance = captured_states[0]
            handlers = mock_key_bindings.captured_handlers

            # Mock event for handlers
            mock_event = Mock()
            mock_event.app = mock_app

            # Test Down
            assert "down" in handlers
            assert state_instance.current == 0
            handlers["down"](mock_event)
            assert state_instance.current == 1
            assert state_instance.selected == "val2"

            # Test Up
            assert "up" in handlers
            handlers["up"](mock_event)
            assert state_instance.current == 0

            # Test Enter
            assert "enter" in handlers
            handlers["enter"](mock_event)
            assert state_instance.finalized is True
            mock_app.exit.assert_called_with(result="val1")

    # Mock everything to bypass type checking in VSplit/HSplit
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.ConditionalContainer")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.Window")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.HSplit")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.VSplit")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.Layout")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.Application")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.TextArea")
    def test_ask_text_simple(
        self, mock_ta, mock_app, mock_layout, mock_vsplit, mock_hsplit, mock_win, mock_cc, mock_key_bindings
    ):
        """Test simple text input."""
        mock_instance = mock_app.return_value
        mock_instance.run.return_value = "input_text"

        # Configure TextArea mock
        mock_field = mock_ta.return_value
        mock_field.text = "result"

        result = ask_text("Enter name")

        assert result == "input_text"

        # Verify handlers registered
        assert "enter" in mock_key_bindings.captured_handlers
        assert "escape" in mock_key_bindings.captured_handlers

    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.ConditionalContainer")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.Window")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.HSplit")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.VSplit")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.Layout")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.Application")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.TextArea")
    def test_ask_text_validation_success(
        self, mock_ta, mock_app, mock_layout, mock_vsplit, mock_hsplit, mock_win, mock_cc, mock_key_bindings
    ):
        """Test validated text input with valid data."""
        mock_instance = mock_app.return_value

        # Configure TextArea mock
        mock_field = mock_ta.return_value
        mock_field.text = "valid_123"
        mock_field.buffer = MagicMock()  # For on_text_changed +=

        ask_text_with_validation("Title", r"^[a-z_0-9]+$", "Error")

        handlers = mock_key_bindings.captured_handlers
        mock_event = Mock()
        mock_event.app = mock_instance

        # Execute Enter handler
        handlers["enter"](mock_event)

        # Should exit because regex matches
        mock_instance.exit.assert_called_with(result="valid_123")

    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.ConditionalContainer")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.Window")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.HSplit")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.VSplit")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.Layout")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.Application")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.TextArea")
    def test_ask_text_validation_fail(
        self, mock_ta, mock_app, mock_layout, mock_vsplit, mock_hsplit, mock_win, mock_cc, mock_key_bindings
    ):
        """Test validated text input with invalid data."""
        mock_instance = mock_app.return_value

        # Configure TextArea mock
        mock_field = mock_ta.return_value
        mock_field.text = "INVALID!!!"
        mock_field.buffer = MagicMock()

        ask_text_with_validation("Title", r"^[a-z]+$", "Error Msg")

        handlers = mock_key_bindings.captured_handlers
        mock_event = Mock()
        mock_event.app = mock_instance

        # Run handler
        handlers["enter"](mock_event)

        # Should NOT exit
        mock_instance.exit.assert_not_called()
        # Should invalidate (redraw) to show error
        mock_instance.invalidate.assert_called()


class TestOutputHelpers:
    """Tests for static output helpers."""

    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.console")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.time.sleep")
    def test_intro_animate_once(self, mock_sleep, mock_console):
        """Test animation prints."""
        intro_animate_once()
        assert mock_console.print.call_count >= 5

    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.console")
    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.time.sleep")
    def test_sandwich_text_ui(self, mock_sleep, mock_console):
        """Test sandwich text ui prints borders."""
        # Set specific width to avoid comparison with MagicMock error
        mock_console.width = 120

        sandwich_text_ui("style", "text")

        # 2 borders + 1 text
        assert mock_console.print.call_count == 3
        # Check that borders were printed
        args, _ = mock_console.print.call_args_list[0]
        # Should print line of dashes
        assert "-" in args[0] or "─" in args[0]

    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.sandwich_text_ui")
    def test_show_invalid_aws_creds(self, mock_sandwich):
        """Test credential validation UI helper."""
        # Case: OK
        assert show_invalid_aws_creds(True, None) is True
        mock_sandwich.assert_not_called()

        # Case: Failed
        assert show_invalid_aws_creds(False, "Error msg") is False
        mock_sandwich.assert_called_once()
        text_arg = mock_sandwich.call_args[1]["text"]
        assert "Error msg" in text_arg
        assert "Log into AWS" in text_arg

    @patch("bedrock_agentcore_starter_toolkit.cli.cli_ui.sandwich_text_ui")
    def test_show_invalid_aws_creds_with_header(self, mock_sandwich):
        """Test credential validation UI with custom header."""
        show_invalid_aws_creds(False, "Err", optional_header="Important!")

        text_arg = mock_sandwich.call_args[1]["text"]
        assert "Important!" in text_arg
