"""UI components for interactive CLI selectors."""

import re
import time
from typing import Optional

from prompt_toolkit.application import Application
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, VSplit
from prompt_toolkit.layout.containers import ConditionalContainer, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.output import ColorDepth
from prompt_toolkit.styles import Style, StyleTransformation
from prompt_toolkit.widgets import TextArea
from rich.control import Control

from ..cli.common import console

PROMPT_TOOLKIT_RICH_CYAN = "ansicyan"
RICH_CYAN = "cyan"

STYLE = Style.from_dict(
    {
        "": "nounderline",
        "title": "",
        "option-name": "fg:default",
        "option-desc": "fg:#777777",
        "cyan": PROMPT_TOOLKIT_RICH_CYAN,
        "selected-bullet": PROMPT_TOOLKIT_RICH_CYAN,
        "selected-name": PROMPT_TOOLKIT_RICH_CYAN,
        "error": "fg:#ff5f5f",
    }
)


class NoUnderline(StyleTransformation):
    """Disable underline styling."""

    def transform_attrs(self, attrs):
        """Return attrs without underline."""
        return attrs._replace(underline=False)


# ---------------------------------------------------------------------------
# STATE + FRAGMENTS
# ---------------------------------------------------------------------------


class OptionState:
    """Track selector cursor and chosen value."""

    def __init__(self, values: list[tuple[str, str, str | None]]):
        """Initialize state with a list of (value, name, desc)."""
        self.values = values
        self.current = 0
        self.selected = values[0][0] if values else None
        self.finalized = False  # <--- Tracks if selection is made

        # Calculate the maximum length of the names for alignment purposes
        self.max_name_len = max((len(n) for _, n, _ in values), default=0)

    @property
    def current_value(self):
        """Return the value at the cursor."""
        return self.values[self.current][0]


def build_option_fragments(state: OptionState):
    """Produce formatted line fragments for the option list."""
    # <--- If finalized, ONLY return the selected line (Collapse effect)
    if state.finalized:
        return [
            ("class:selected-name", state.selected or ""),
            ("", "\n"),
        ]

    # Standard rendering logic
    frags = []
    for idx, (val, name, desc) in enumerate(state.values):
        is_cursor = idx == state.current
        is_checked = val == state.selected

        if is_cursor:
            prefix_style = "class:cyan"
            bullet_style = "class:cyan"
            name_style = "class:selected-name"
        else:
            prefix_style = ""
            bullet_style = "class:option-name"
            name_style = "class:option-name"

        cursor_prefix = "> " if is_cursor else "  "
        bullet = "● " if is_checked else "○ "

        frags.append((prefix_style, cursor_prefix))
        frags.append((bullet_style, bullet))
        frags.append((name_style, name))

        if desc and desc.strip():
            required_padding = state.max_name_len - len(name)
            pad_len = min(required_padding, 7)
            padding = " " * pad_len
            frags.append(("class:option-desc", f"{padding} - {desc}"))

        frags.append(("", "\n"))

    return frags


# ---------------------------------------------------------------------------
# WELCOME SCREEN
# ---------------------------------------------------------------------------


def show_create_welcome_ascii() -> None:
    """Display the simple welcome message."""
    console.print()
    sandwich_text_ui(style=RICH_CYAN, text="[cyan]🤖 AgentCore activated.[/cyan] Let's build your agent.")


# ---------------------------------------------------------------------------
# SELECT-ONE CONTROL
# ---------------------------------------------------------------------------


def select_one(title: str, options: list[str] | dict[str, str], default: str | None = None):
    """Interactive single-choice selector."""
    if isinstance(options, dict):
        values = [(val, val, desc) for val, desc in options.items()]
    else:
        values = [(val, val, None) for val in options]

    state = OptionState(values)

    if "(optional)" in title:
        main_text, _, remainder = title.partition("(optional)")
        title_fragments = [
            ("class:title", main_text),
            ("", "(optional)"),  # Uses terminal default (no bold, default color)
            ("class:title", remainder),
        ]
    else:
        title_fragments = [("class:title", title)]

    options_control = FormattedTextControl(
        lambda: build_option_fragments(state),
        focusable=True,
        show_cursor=False,
    )

    # Note: We keep the title separate so it stays visible even after collapse
    title_window = Window(
        FormattedTextControl(title_fragments, focusable=False),
        height=1,
        dont_extend_height=True,
    )

    options_window = Window(
        options_control,
        always_hide_cursor=True,
        wrap_lines=False,
    )

    kb = KeyBindings()

    @kb.add("down")
    def _(e):
        if not state.finalized and state.current < len(state.values) - 1:
            state.current += 1
        state.selected = state.current_value
        e.app.invalidate()

    @kb.add("up")
    def _(e):
        if not state.finalized and state.current > 0:
            state.current -= 1
        state.selected = state.current_value
        e.app.invalidate()

    @kb.add("enter")
    def _(e):
        # <--- Don't exit immediately.
        # 1. Lock state
        state.selected = state.current_value
        state.finalized = True

        # 2. Force one last redraw (which will trigger the "collapsed" view)
        # 3. Then exit
        e.app.exit(result=state.current_value)

    @kb.add("escape")
    @kb.add("c-c")
    def _(e):
        raise KeyboardInterrupt

    root = HSplit(
        [
            title_window,
            options_window,
        ]
    )

    app = Application(
        layout=Layout(root, focused_element=options_window),
        key_bindings=kb,
        style=STYLE,
        style_transformation=NoUnderline(),
        color_depth=ColorDepth.DEPTH_24_BIT,
        erase_when_done=False,  # <--- IMPORTANT: Keep the last frame on screen
        full_screen=False,
        mouse_support=False,
    )

    result = app.run()
    # No manual print here! The "collapsed" UI frame remains as the print record.
    time.sleep(0.1)
    return result


# ---------------------------------------------------------------------------
# ASK TEXT INPUT
# ---------------------------------------------------------------------------


def ask_text(
    title: str,
    default: str | None = None,
    redact: bool = False,
    starting_chars: str = "> ",
    erase_prompt_on_submit: bool = True,
) -> str | None:
    """Prompt user for a single-line text value."""
    is_active = True

    @Condition
    def show_prompt():
        # Show if we are NOT erasing, OR if we are still active
        return not erase_prompt_on_submit or is_active

    field = TextArea(
        text=default or "",
        multiline=False,
        style="class:cyan",
        focus_on_click=True,
        wrap_lines=False,
        password=redact,
    )
    field.buffer.cursor_position = len(field.text)

    kb = KeyBindings()

    @kb.add("enter")
    def _(ev):
        nonlocal is_active
        is_active = False
        ev.app.exit(result=field.text.strip())

    @kb.add("escape")
    @kb.add("c-c")
    def _(ev):
        raise KeyboardInterrupt

    # Always use ConditionalContainer, logic handles the persistence
    prompt_container = ConditionalContainer(
        content=Window(FormattedTextControl([("class:cyan", starting_chars)]), width=len(starting_chars), align="left"),
        filter=show_prompt,
    )

    input_row = VSplit(
        [
            prompt_container,
            field,
        ],
        height=1,
    )

    root = HSplit(
        [
            Window(FormattedTextControl([("class:title", title)]), height=1),
            input_row,
        ]
    )

    app = Application(
        layout=Layout(root, focused_element=field),
        key_bindings=kb,
        style=STYLE,
        style_transformation=NoUnderline(),
        erase_when_done=False,
        full_screen=False,
        color_depth=ColorDepth.DEPTH_24_BIT,
        mouse_support=False,
    )

    result = app.run()
    _pause_and_new_line_on_finish()
    return result


# ---------------------------------------------------------------------------
# ASK TEXT WITH VALIDATION
# ---------------------------------------------------------------------------


def ask_text_with_validation(
    title: str,
    regex: str,
    error_message: str,
    default: str | None = None,
    redact: bool = False,
    starting_chars: str = "> ",
    erase_prompt_on_submit: bool = True,
) -> str:
    """Prompt user for text with regex validation."""
    state = {"error": ""}
    is_active = True

    @Condition
    def show_prompt():
        return not erase_prompt_on_submit or is_active

    field = TextArea(
        text=default or "",
        multiline=False,
        style="class:cyan",
        focus_on_click=True,
        wrap_lines=False,
        password=redact,
    )
    field.buffer.cursor_position = len(field.text)

    # Helper to show text only if error exists
    def get_error_text():
        return [("class:error", f"{state['error']}")]

    # Condition: Only show the error window if state['error'] is not empty
    has_error = Condition(lambda: bool(state["error"]))

    kb = KeyBindings()

    @kb.add("enter")
    def _(ev):
        val = field.text.strip()
        if re.fullmatch(regex, val):
            nonlocal is_active
            is_active = False
            ev.app.exit(result=val)
        else:
            state["error"] = error_message
            ev.app.invalidate()

    @kb.add("escape")
    @kb.add("c-c")
    def _(ev):
        raise KeyboardInterrupt

    def on_text_changed(_):
        if state["error"]:
            state["error"] = ""

    field.buffer.on_text_changed += on_text_changed

    prompt_container = ConditionalContainer(
        content=Window(
            FormattedTextControl([("class:cyan", starting_chars)]),
            width=len(starting_chars),
            dont_extend_width=True,
        ),
        filter=show_prompt,
    )

    input_row = VSplit(
        [
            prompt_container,
            field,
        ],
        height=1,
    )

    # ConditionalContainer ensures this takes 0 height when there is no error
    error_row = ConditionalContainer(content=Window(FormattedTextControl(get_error_text), height=1), filter=has_error)

    root = HSplit(
        [
            Window(FormattedTextControl([("class:title", title)]), height=1),
            input_row,
            error_row,  # Only appears on error
        ]
    )

    app = Application(
        layout=Layout(root, focused_element=field),
        key_bindings=kb,
        style=STYLE,
        style_transformation=NoUnderline(),
        erase_when_done=False,
        full_screen=False,
        color_depth=ColorDepth.DEPTH_24_BIT,
        mouse_support=False,
    )

    result = app.run()
    _pause_and_new_line_on_finish()
    return result


def intro_animate_once():
    """Animation at the beginning of project generation."""
    base = "Agent initializing"

    console.print(Control.show_cursor(show=False))
    try:
        for dots in ["", ".", "..", "..."]:
            console.print(f"{base}{dots}", end="\r", highlight=False, markup=False)
            time.sleep(0.25)
        console.print(f"{base}...", highlight=False, markup=False)
    finally:
        console.print(Control.show_cursor(show=True))


def print_border(char: str = "-", style: str = "") -> None:
    """Print a border spanning up to 100 chars."""
    safe_width = min(console.width, 100)
    console.print(char * safe_width, style=style)


def sandwich_text_ui(style: str, text: str) -> None:
    """Wrap the input in border."""
    print_border(style=style)
    console.print(text)
    print_border(style=style)
    _pause_and_new_line_on_finish()


def show_invalid_aws_creds(ok: bool, msg: Optional[str], optional_header: Optional[str] = None) -> bool:
    """Standard UI messaging for AWS credential validation.

    Returns True if creds are valid, False otherwise.
    """
    if ok:
        return True

    header_text = f"{optional_header}\n\n" if optional_header else ""
    error_msg_text = f"Exception message: {msg}" if msg else ""
    sandwich_text_ui(
        style="yellow",
        text=(
            f"{header_text}"
            f"Environment does not contain valid AWS credentials\n"
            f"{error_msg_text}\n"
            f"[cyan]Log into AWS with `aws login` or add credentials to your environment to continue[/cyan]"
        ),
    )
    return False


def _pause_and_new_line_on_finish(sleep_override: float | None = None):
    """Sleep and print a line for polish after a command finishes."""
    time.sleep(sleep_override or 0.10)
    print()
