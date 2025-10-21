import time

import typer

from ... import events
from ...spawn import registry
from ..renderer import Event, Renderer

app = typer.Typer()


def _stream_events(channel: str | None = None):
    """Helper function to stream bridge events, with optional channel filtering."""

    try:
        all_events = events.query(source="bridge", limit=1000)
    except Exception as e:
        typer.echo(f"❌ Error querying historic events: {e}")
        all_events = []

    for event_tuple in reversed(all_events):
        event = {
            "uuid": event_tuple[0],
            "source": event_tuple[1],
            "identity": event_tuple[2],
            "event_type": event_tuple[3],
            "data": event_tuple[4],
            "created_at": event_tuple[5],
        }
        if channel is None or (
            event.get("data") and event.get("data", {}).get("channel") == channel
        ):
            event_type = event.get("event_type")
            data = event.get("data", {})
            identity = event.get("identity")
            if event_type == "message_sent":
                typer.echo(f"→ Sent to {data.get('channel')} as {identity}: {data.get('content')}")
            elif event_type == "message_received":
                sender = registry.get_identity(data.get('agent_id'))
                channel = data.get('channel')
                content = data.get('content')
                typer.echo(f"← Received from {sender} in {channel}: {content}")

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
                            "data": event_tuple[4],
                            "created_at": event_tuple[5],
                        }
                        if channel is None or (
                            event_data.get("data")
                            and event_data.get("data", {}).get("channel") == channel
                        ):
                            event_type = event_data.get("event_type")
                            data = event_data.get("data", {})
                            if event_type == "message_sent":
                                channel = data.get('channel')
                                identity = event_data.get('identity')
                                content = data.get('content')
                                msg = f"→ Sent to {channel} as {identity}: {content}\n"
                                yield Event(type="token", content=msg)
                            elif event_type == "message_received":
                                sender = registry.get_identity(data.get('agent_id'))
                                channel = data.get('channel')
                                content = data.get('content')
                                msg = f"← Received from {sender} in {channel}: {content}\n"
                                yield Event(type="token", content=msg)
                            else:
                                yield Event(type="status", content=f"Event: {event_type}")

                    last_event_uuid = new_events[0][0]

                time.sleep(1)
            except KeyboardInterrupt:
                yield Event(type="done")
                break
            except Exception as e:
                yield Event(type="error", content=f"Error streaming events: {e}")
                time.sleep(1)

    renderer.render(event_stream())


@app.command()
def stream():
    """Stream all bridge events in real-time."""
    _stream_events()


@app.command()
def council(
    channel: str = typer.Argument(...),
):
    """Stream bridge events for a specific channel."""
    _stream_events(channel=channel)
