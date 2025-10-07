from . import repository
from .models import Channel, Message, Note, ExportData

def create_channel(channel_name: str, guide_hash: str) -> str:
    repository.initialize()
    return repository.create_channel(channel_name, guide_hash)

def get_channel_id(channel_name: str) -> str | None:
    repository.initialize()
    return repository.get_channel_id(channel_name)

def create_message(channel_id: str, sender: str, content: str, prompt_hash: str) -> int:
    repository.initialize()
    return repository.create_message(channel_id, sender, content, prompt_hash)

def get_messages_for_channel(channel_id: str) -> list[Message]:
    repository.initialize()
    return repository.get_messages_for_channel(channel_id)

__all__ = ["cli", "create_channel", "get_channel_id", "create_message", "get_messages_for_channel", "Channel", "Message", "Note", "ExportData"]
