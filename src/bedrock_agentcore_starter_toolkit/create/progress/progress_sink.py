"""Context manager utility to show progress to user."""

import time
from contextlib import contextmanager

from rich.live import Live
from rich.padding import Padding
from rich.spinner import Spinner
from rich.text import Text

from ...cli.common import console


class ProgressSink:
    """Handles indented sub-steps with physically indented spinners."""

    MIN_PHASE_SECONDS = 1.0
    STYLE = "cyan"
    INDENT_SPACES = 4

    @contextmanager
    def step(self, message: str, done_message: str | None = None, error_message: str | None = None, swallow_fail=False):
        """Wrap a process in a with: context block.

        Args:
        message: The text to show next to the spinner.
        done_message: The text to show when finished successfully.
        error_message: If provided, we catch exceptions, print this message,
                       and THEN re-raise the exception.
        swallow_fail: Whether to re-raise an exception if it occurs.
        """
        start = time.time()

        # 1. Prepare Spinner
        spinner_text = Text.from_markup(f"[{self.STYLE}] {message}...[/]")
        spinner = Spinner("dots", text=spinner_text, style=self.STYLE)
        indented_spinner = Padding(spinner, (0, 0, 0, self.INDENT_SPACES))

        success = False

        with Live(indented_spinner, console=console, refresh_per_second=12, transient=True):
            try:
                yield
                success = True
            except Exception:
                # ONLY handle the UI for the error if a message was provided
                if error_message:
                    # Use standard style (no red)
                    fail_text = Text.from_markup(f"[{self.STYLE}]• {error_message}.[/]")
                    indented_fail = Padding(fail_text, (0, 0, 0, self.INDENT_SPACES))
                    console.print(indented_fail)
                if not swallow_fail:
                    raise
            finally:
                # Enforce minimum duration regardless of success/fail
                elapsed = time.time() - start
                if elapsed < self.MIN_PHASE_SECONDS:
                    time.sleep(self.MIN_PHASE_SECONDS - elapsed)

        # 2. Handle Success (Outside the Live context so it persists)
        if success:
            final_msg = done_message or "done"
            bullet_text = Text.from_markup(f"[{self.STYLE}]• {final_msg}.[/]")
            indented_bullet = Padding(bullet_text, (0, 0, 0, self.INDENT_SPACES))
            console.print(indented_bullet)
