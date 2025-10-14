from datetime import datetime

from space.models import Export
from space.spawn.registry import get_agent_name


def resolve_agent_names(export_data: Export) -> Export:
    """Resolve agent IDs to names in an Export object."""
    participants = [get_agent_name(p) or p for p in export_data.participants]
    messages = []
    for msg in export_data.messages:
        msg.sender = get_agent_name(msg.sender) or msg.sender
        messages.append(msg)

    notes = []
    for note in export_data.notes:
        note.author = get_agent_name(note.author) or note.author
        notes.append(note)

    return Export(
        channel_id=export_data.channel_id,
        channel_name=export_data.channel_name,
        topic=export_data.topic,
        created_at=export_data.created_at,
        participants=participants,
        message_count=export_data.message_count,
        messages=messages,
        notes=notes,
    )


def format_channel_meta(channel) -> str:
    """Create a metadata string for a channel."""
    parts = []
    msgs = channel.message_count
    members = len(channel.participants)
    notes = channel.notes_count

    if msgs == 1:
        parts.append("1 msg")
    elif msgs > 1:
        parts.append(f"{msgs} msgs")

    if members == 1:
        parts.append("1 member")
    elif members > 1:
        parts.append(f"{members} members")

    if notes == 1:
        parts.append("1 note")
    elif notes > 1:
        parts.append(f"{notes} notes")
    return " | ".join(parts)


def format_channel_row(channel) -> tuple[str, str]:
    """Formats a channel object into a tuple of (last_activity_str, channel_info_str)."""
    if channel.last_activity:
        last_activity = datetime.fromisoformat(channel.last_activity).strftime("%Y-%m-%d")
    else:
        last_activity = "never"
    meta_str = format_channel_meta(channel)
    return last_activity, f"{channel.name} - {meta_str}"
