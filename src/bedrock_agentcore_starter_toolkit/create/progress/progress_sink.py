"""ProgressSink impl to surface progress to user."""

import time
from contextlib import contextmanager

from rich.live import Live
from rich.padding import Padding
from rich.spinner import Spinner
from rich.text import Text

from ...cli.common import console


class ProgressSink:
    """Handles indented sub-steps with physically indented spinners.

    Use with the 'Sandwich Pattern' (Print Header -> Steps -> Print Footer).
    """

    MIN_PHASE_SECONDS = 1.0
    STYLE = "cyan"
    INDENT_SPACES = 4

    @contextmanager
    def step(self, message: str, done_message: str | None = None):
        """ex: with sink.step("Creating venv", "Created venv")."""
        start = time.time()

        # 1. Prepare the Spinner
        # We add a space before the message so it doesn't hug the spinner icon
        spinner_text = Text.from_markup(f"[{self.STYLE}] {message}...[/]")
        spinner = Spinner("dots", text=spinner_text, style=self.STYLE)

        # 2. Indent the Spinner using Padding
        indented_spinner = Padding(spinner, (0, 0, 0, self.INDENT_SPACES))

        # 3. Run the Live display
        with Live(indented_spinner, console=console, refresh_per_second=12, transient=True):
            try:
                yield
            finally:
                # enforce minimum duration
                elapsed = time.time() - start
                if elapsed < self.MIN_PHASE_SECONDS:
                    time.sleep(self.MIN_PHASE_SECONDS - elapsed)

        # 4. Prepare the Success Line
        final_msg = done_message or "done"
        # Create a Text object for the bullet line (Bullet + Space + Message)
        bullet_text = Text.from_markup(f"[{self.STYLE}]• {final_msg}.[/]")

        # 5. Indent the Success Line using the SAME Padding logic
        # This guarantees the alignment matches the spinner exactly
        indented_bullet = Padding(bullet_text, (0, 0, 0, self.INDENT_SPACES))
        console.print(indented_bullet)
