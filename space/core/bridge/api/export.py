"""Export operations: get full channel transcript."""

from space.core.models import Export

from . import channels as ch


def get_export_data(channel_id: str) -> Export:
    """Get complete channel export with messages and notes."""
    return ch.export_channel(channel_id)
