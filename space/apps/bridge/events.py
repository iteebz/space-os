from __future__ import annotations

from .. import events


def emit(event_type: str, data: dict | None = None, identity: str | None = None) -> None:
    """Emits a structured event from the bridge."""
    events.track(source="bridge", identity=identity, event_type=event_type, data=data)
