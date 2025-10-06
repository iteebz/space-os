import json
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Optional

import click

from space.os import events
from space.apps.bridge.renderer import Event, Renderer


def stream_events(channel_name: str | None = None):
    """Helper function to stream bridge events, with optional channel filtering."""
    # 1. Render historic events
    all_events = events.query(source="bridge", limit=1000)  # Increased limit for history
    for event_tuple in reversed(all_events):
        event = {
            "uuid": event_tuple[0],
            "source": event_tuple[1],
            "identity": event_tuple[2],
            "data": json.loads(event_tuple[4])
            if isinstance(event_tuple[4], str)
            else event_tuple[4],
            "created_at": event_tuple[5],
        }
        if channel_name is None or (
            event.get("data") and event.get("data", {}).get("channel") == channel_name
        ):
            event_type = event.get("event_type")
            data = event.get("data", {})
            identity = event.get("identity")
            if event_type == "message_sent":
                click.echo(f"→ Sent to {data.get('channel')} as {identity}: {data.get('content')}")
            elif event_type == "message_received":
                click.echo(
                    f"← Received from {data.get('sender_id')} in {data.get('channel')}: {data.get('content')}"
                )

    # 2. Start live stream
    renderer = Renderer()

    def event_stream():
        last_event_uuid = all_events[0][0] if all_events else None
        while True:
            try:
                all_events_live = events.query(source="bridge", limit=100)
                new_events = []
                if last_event_uuid:
                    for i, event in enumerate(all_events_live):
                        if event[0] == last_event_uuid:
                            new_events = all_events_live[:i]
                            break
                else:
                    new_events = all_events_live

                if new_events:
                    for event_tuple in reversed(new_events):
                        event_data = {
                            "uuid": event_tuple[0],
                            "source": event_tuple[1],
                            "identity": event_tuple[2],
                            "event_type": event_tuple[3],
                            "data": json.loads(event_tuple[4])
                            if isinstance(event_tuple[4], str)
                            else event_tuple[4],
                            "created_at": event_tuple[5],
                        }
                        if channel_name is None or (
                            event_data.get("data")
                            and event_data.get("data", {}).get("channel") == channel_name
                        ):
                            event_type = event_data.get("event_type")
                            data = event_data.get("data", {})
                            if event_type == "message_sent":
                                yield Event(
                                    type="token",
                                    content=f"→ Sent to {data.get('channel')} as {event_data.get('identity')}: {data.get('content')}\n",
                                )
                            elif event_type == "message_received":
                                yield Event(
                                    type="token",
                                    content=f"← Received from {data.get('sender_id')} in {data.get('channel')}: {data.get('content')}\n",
                                )
                            else:
                                yield Event(type="status", content=f"Event: {event_type}")

                    last_event_uuid = new_events[0][0]

                time.sleep(1)
            except KeyboardInterrupt:
                yield Event(type="done")
                break

    renderer.render(event_stream())
