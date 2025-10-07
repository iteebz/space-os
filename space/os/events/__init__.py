from typing import Any, Callable
from collections import defaultdict

from . import repository
from .models import Event

# In-memory listener registry (Pub/Sub)
_listeners = defaultdict(list)

def on(event_type: str | None = None, source: str | None = None) -> Callable:
    """Decorator to register a function as an event listener."""
    def decorator(func: Callable):
        _listeners[(event_type, source)].append(func)
        return func
    return decorator

def emit(event: Event):
    """Dispatches an event to registered listeners."""
    # Dispatch to specific listeners (event_type, source)
    for listener in _listeners[(event.event_type, event.source)]:
        listener(event)
    # Dispatch to general listeners (event_type, None)
    for listener in _listeners[(event.event_type, None)]:
        listener(event)
    # Dispatch to general listeners (None, source)
    for listener in _listeners[(None, event.source)]:
        listener(event)
    # Dispatch to global listeners (None, None)
    for listener in _listeners[(None, None)]:
        listener(event)

def track(source: str, event_type: str, identity: str | None = None, data: dict | None = None):
    """
    Records an event to the database and dispatches it to listeners.
    """
    repository.initialize()
    event_id = repository.add(source, event_type, identity, data)
    
    # We need to get the full event object to emit it
    # This is a slight impurity, but it's a pragmatic choice to keep the repository simple.
    # A purer solution might involve the `add` function returning the full event object.
    from .repository import _connect, _row_to_entity
    with _connect() as conn:
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if row:
            emit(_row_to_entity(row))

__all__ = ["track", "emit", "on", "Event"]
