"""Chat operations: discover, sync, stats."""

from space.lib import paths
from space.lib import sync as lib_sync


def sync_all_providers(on_progress=None) -> dict[str, tuple[int, int]]:
    """Sync chats from all providers to ~/.space/chats/.

    Args:
        on_progress: Optional callback function that receives ProgressEvent

    Returns:
        {provider_name: (sessions_discovered, files_synced)} for each provider
    """
    return lib_sync.sync_provider_chats(on_progress=on_progress)


def resync_chat(session_id: str) -> dict[str, tuple[int, int]]:
    """Resync a specific chat session, updating metadata and linking to task.

    Args:
        session_id: The session ID to resync

    Returns:
        {provider_name: (sessions_discovered, files_synced)} for that provider
    """
    return lib_sync.sync_provider_chats(session_id=session_id)


def get_provider_stats() -> dict[str, dict]:
    """Get chat statistics across all providers.

    Returns:
        {provider_name: {"files": int, "size_mb": float}} for each provider
    """
    chats_dir = paths.chats_dir()
    stats = {}

    if not chats_dir.exists():
        return stats

    for provider_dir in chats_dir.iterdir():
        if not provider_dir.is_dir():
            continue

        provider_name = provider_dir.name
        files = list(provider_dir.rglob("*"))
        file_count = sum(1 for f in files if f.is_file())
        size_bytes = sum(f.stat().st_size for f in files if f.is_file())
        size_mb = size_bytes / (1024 * 1024)

        stats[provider_name] = {
            "files": file_count,
            "size_mb": size_mb,
        }

    return stats
