from __future__ import annotations

import json

from .. import events


def emit(event_type: str, data: dict | None = None, identity: str | None = None) -> None:
    """Emits a structured event from the bridge."""
    data_str = json.dumps(data) if data is not None else None
    events.emit(source="bridge", identity=identity, event_type=event_type, data=data_str)
