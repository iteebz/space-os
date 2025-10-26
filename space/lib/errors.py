"""Error capture for CLI commands."""

import sys


def install_error_handler(source: str):
    """Install sys.excepthook to log uncaught exceptions."""
    original_hook = sys.excepthook

    def error_hook(exc_type, exc_value, exc_traceback):
        if exc_type.__name__ not in ("Exit", "Abort", "KeyboardInterrupt"):
            f"{exc_type.__name__}: {str(exc_value)}"

        original_hook(exc_type, exc_value, exc_traceback)

    sys.excepthook = error_hook


def log_error(source: str, agent_id: str | None, error: Exception, command: str = ""):
    """Log error to events with agent context and command."""
    if command:
        f"{command}: {type(error).__name__}: {str(error)}"
    else:
        f"{type(error).__name__}: {str(error)}"
