"""Juicy terminal spinner for long-running operations."""

import sys


class Spinner:
    """Animated spinner with message updates."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self):
        """Initialize spinner."""
        self.tick_count = 0
        self.message = ""

    def update(self, message: str) -> None:
        """Update spinner with new message."""
        self.message = message
        frame = self.FRAMES[(self.tick_count // 5) % len(self.FRAMES)]
        sys.stderr.write(f"\r{frame} {message}")
        sys.stderr.flush()
        self.tick_count += 1

    def finish(self, message: str = "Done") -> None:
        """Finish spinner with final message."""
        sys.stderr.write(f"\r✓ {message}".ljust(40) + "\n")
        sys.stderr.flush()
