"""Export operations: get full channel transcript."""

from space.os.models import Export

from . import channels as ch
from . import messaging
from . import notes as nt


def get_export_data(channel_id: str) -> Export:
    """Get complete channel export with messages and notes."""
    topic = ch.get_topic(channel_id)
    channel_name = ch.get_channel_name(channel_id)
    messages = messaging.get_all_messages(channel_id)
    notes_list = nt.get_notes(channel_id)
    participants = ch.get_participants(channel_id)

    created_at = None
    if messages:
        created_at = messages[0].created_at

    return Export(
        channel_id=channel_id,
        channel_name=channel_name,
        topic=topic,
        created_at=created_at,
        participants=participants,
        message_count=len(messages),
        messages=messages,
        notes=notes_list,
    )
