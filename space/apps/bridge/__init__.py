from .repo import BridgeRepo

# Instantiate the repository, which is now a self-contained component.
repo = BridgeRepo()

# Expose the repository methods as the public API of the app.
def create_channel(channel_name: str, guide_hash: str) -> str:
    return repo.create_channel(channel_name, guide_hash)

def get_channel_id(channel_name: str) -> str | None:
    return repo.get_channel_id(channel_name)

def get_channel_name(channel_id: str) -> str | None:
    return repo.get_channel_name(channel_id)

def create_message(channel_id: str, sender: str, content: str, prompt_hash: str) -> int:
    return repo.create_message(channel_id, sender, content, prompt_hash)

def get_messages_for_channel(channel_id: str) -> list:
    return repo.get_messages_for_channel(channel_id)

def fetch_sender_history(sender: str, limit: int | None = None) -> list:
    return repo.fetch_sender_history(sender, limit)

__all__ = [
    "create_channel",
    "get_channel_id",
    "get_channel_name",
    "create_message",
    "get_messages_for_channel",
    "fetch_sender_history",
    "repo", # Exposing the repo directly for now
]
