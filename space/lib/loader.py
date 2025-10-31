"""Progress loader for long-running operations like chat sync."""

from dataclasses import dataclass


@dataclass
class ProgressEvent:
    """Progress event with provider and counts."""

    provider: str
    discovered: int
    synced: int
    total_discovered: int = 0
    total_synced: int = 0


class ProgressLoader:
    """Minimal progress loader for sync operations.

    Usage:
        loader = ProgressLoader(on_progress=print_progress)
        results = sync_provider_chats(on_progress=loader.on_event)
    """

    def __init__(self, on_progress: callable | None = None):
        """Initialize loader with optional callback.

        Args:
            on_progress: Callback function that receives ProgressEvent
        """
        self.on_progress = on_progress
        self.events = []

    def on_event(self, event: ProgressEvent) -> None:
        """Handle progress event."""
        self.events.append(event)
        if self.on_progress:
            self.on_progress(event)
