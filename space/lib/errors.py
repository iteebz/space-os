"""Error capture for CLI commands."""

import contextlib
import sys

from ..core import events


def install_error_handler(source: str):
    """Install sys.excepthook to log uncaught exceptions."""
    original_hook = sys.excepthook

    def error_hook(exc_type, exc_value, exc_traceback):
        if exc_type.__name__ not in ("Exit", "Abort", "KeyboardInterrupt"):
            error_msg = f"{exc_type.__name__}: {str(exc_value)}"

            with contextlib.suppress(Exception):
                events.emit(source, "error", None, error_msg)

        original_hook(exc_type, exc_value, exc_traceback)

    sys.excepthook = error_hook


def log_error(source: str, agent_id: str | None, error: Exception, command: str = ""):
    """Log error to events with agent context and command."""
    if command:
        error_msg = f"{command}: {type(error).__name__}: {str(error)}"
    else:
        error_msg = f"{type(error).__name__}: {str(error)}"
    events.emit(source, "error", agent_id, error_msg)
