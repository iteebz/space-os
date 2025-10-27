"""Chat operations: discover, sync, stats."""

from pathlib import Path

from space.lib import paths, sync as lib_sync


def sync_all_providers() -> dict[str, tuple[int, int]]:
    """Sync chats from all providers to ~/.space/chats/.
    
    Returns:
        {provider_name: (sessions_discovered, files_synced)} for each provider
    """
    return lib_sync.sync_provider_chats()


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
