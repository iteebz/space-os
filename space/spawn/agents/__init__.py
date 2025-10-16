from typing import Protocol


class Agent(Protocol):
    """Agent protocol for ephemeral spawning."""

    def run(self, prompt: str | None = None) -> str:
        """Run agent. None = interactive, str = one-shot task."""
        ...
