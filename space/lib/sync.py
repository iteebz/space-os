"""Chat sync: discover and copy provider chats to ~/.space/chats/{provider}/"""

import shutil
from pathlib import Path

from space.lib import paths, providers


def sync_provider_chats(verbose: bool = False) -> dict[str, tuple[int, int]]:
    """Sync chats from all providers (~/.claude, ~/.codex, ~/.gemini) to ~/.space/chats/.

    Only syncs files that are newer than existing copies (diff-aware).

    Args:
        verbose: If True, yield progress messages (not implemented here, use return value)

    Returns:
        {provider_name: (sessions_discovered, files_synced)} for each provider
    """
    results = {}
    chats_dir = paths.chats_dir()
    chats_dir.mkdir(parents=True, exist_ok=True)

    provider_map = {"claude": "Claude", "codex": "Codex", "gemini": "Gemini"}

    for cli_name, class_name in provider_map.items():
        try:
            provider_class = getattr(providers, class_name)
            provider = provider_class()

            sessions = provider.discover_sessions()
            if not sessions:
                results[cli_name] = (0, 0)
                continue

            dest_dir = chats_dir / cli_name
            dest_dir.mkdir(parents=True, exist_ok=True)

            synced_count = 0
            for session in sessions:
                src_file = Path(session["file_path"])
                if not src_file.exists():
                    continue

                try:
                    dest_file = dest_dir / src_file.name
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    should_sync = (
                        not dest_file.exists()
                        or src_file.stat().st_mtime > dest_file.stat().st_mtime
                    )

                    if should_sync:
                        shutil.copy2(src_file, dest_file)
                        synced_count += 1
                except (OSError, Exception):
                    pass

            results[cli_name] = (len(sessions), synced_count)
        except (AttributeError, Exception):
            results[cli_name] = (0, 0)

    return results
