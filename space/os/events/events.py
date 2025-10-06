from datetime import datetime
from typing import Callable, Any
from collections import defaultdict
import json

from space.os.lib import uuid7
from .models import Event
from .repo import EventRepo

# Initialize the EventRepo
_event_repo = EventRepo()

# In-memory listener registry
_listeners = defaultdict(list) # { (event_type, source): [listeners] }

def track(source: str, event_type: str, identity: str | None = None, data: dict | None = None):
    """
    Records and dispatches an event.
    """
    event_id = str(uuid7.uuid7())
    timestamp = int(datetime.now().timestamp())

    event = Event(
        id=event_id,
        timestamp=timestamp,
        source=source,
        event_type=event_type,
        identity=identity,
        data=data,
    )

    _event_repo.add(event.source, event.event_type, event.identity, event.data)
    emit(event)

def emit(event: Event):
    """
    Dispatches an event to registered listeners.
    """
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

def on(event_type: str | None = None, source: str | None = None) -> Callable:
    """
    Decorator to register a function as an event listener.
    """
    def decorator(func: Callable):
        _listeners[(event_type, source)].append(func)
        return func
    return decorator
