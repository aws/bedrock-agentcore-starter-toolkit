"""Deprecated command utilities."""

import functools

import typer


def deprecated_command(new_command: str):
    """Decorator to add deprecation warning to commands.

    We are currently using this for the `launch` command.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            typer.echo(
                f"⚠️  Warning: This command name has been deprecated. Use '{new_command}' instead, "
                "which provides the same exact capability and behavior.",
                err=True,
            )
            return func(*args, **kwargs)

        # Update docstring to show deprecation in help
        wrapper.__doc__ = (
            f"⚠️  This command name has been deprecated. Use '{new_command}' instead, "
            f"which provides the same exact capability and behavior.\n\n{func.__doc__ or ''}"
        )
        return wrapper

    return decorator
