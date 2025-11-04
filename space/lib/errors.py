import sys


def install_error_handler(source: str):
    original_hook = sys.excepthook

    def error_hook(exc_type, exc_value, exc_traceback):
        if exc_type.__name__ not in ("Exit", "Abort", "KeyboardInterrupt"):
            print(f"{exc_type.__name__}: {str(exc_value)}", file=sys.stderr)

        original_hook(exc_type, exc_value, exc_traceback)

    sys.excepthook = error_hook


def log_error(source: str, agent_id: str | None, error: Exception, command: str = ""):
    if command:
        print(f"{command}: {type(error).__name__}: {str(error)}", file=sys.stderr)
    else:
        print(f"{type(error).__name__}: {str(error)}", file=sys.stderr)
