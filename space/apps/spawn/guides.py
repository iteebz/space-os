from pathlib import Path
from typing import Optional

from space.os.lib.fs import root
from space.os.lib import sha256 # Import sha256
from space.os import events # Import events for tracking
from . import api as spawn_api


def _prompts_guides_dir() -> Path:
    """Return the absolute path to the prompts/guides directory."""
    return root() / "prompts" / "guides"


def get_guide_from_spawn(guide_hash: str) -> str | None:
    """Retrieve guide content from the spawn by its hash."""
    constitution = spawn_api.get_constitution_by_hash(guide_hash)
    return constitution.content if constitution else None


def _track_guide_access_event(guide_name: str, guide_path: Optional[Path], guide_hash_requested: Optional[str]):
    """Tracks an event when a guide access is attempted."""
    events.track(
        source="spawn",
        event_type="guide.accessed",
        identity=None, # Agent identity will be passed from the caller if available
        data={
            "guide_name": guide_name,
            "guide_path": str(guide_path) if guide_path else None,
            "guide_hash_requested": guide_hash_requested,
        },
        metadata={
            "description": f"Attempting to load guide: {guide_name}"
        }
    )

def _track_guide_loaded_event(guide_name: str, guide_hash: str, loaded_from: str):
    """Tracks an event when a guide is successfully loaded."""
    events.track(
        source="spawn",
        event_type="guide.loaded",
        identity=None, # Agent identity will be passed from the caller if available
        data={
            "guide_name": guide_name,
            "guide_hash": guide_hash,
            "loaded_from": loaded_from
        },
        metadata={
            "description": f"Guide loaded from {loaded_from}: {guide_name}"
        }
    )

def _track_guide_load_failed_event(guide_name: str, guide_path: Optional[Path], reason: str):
    """Tracks an event when a guide fails to load."""
    events.track(
        source="spawn",
        event_type="guide.load_failed",
        identity=None, # Agent identity will be passed from the caller if available
        data={
            "guide_name": guide_name,
            "guide_path": str(guide_path) if guide_path else None,
            "reason": reason
        },
        metadata={
            "description": f"Guide load failed for {guide_name}: {reason}"
        }
    )

def _auto_register_guide_if_needed(guide_name: str, content: str, current_hash: str):
    """Registers a guide in the spawn if it's not already tracked."""
    if not get_guide_from_spawn(current_hash):
        spawn_api.add_constitution_version(
            name=guide_name, # Use the guide_name as the constitution name
            content=content,
            change_description="Auto-tracked guide from file system",
            created_by="spawn_app",
        )

def load_guide_content(guide_name: str, guide_path: Path | None = None, guide_hash: str | None = None) -> str:
    """
    Load the content of a guide.
    Prioritizes loading from spawn if guide_hash is provided.
    If guide_path is provided, loads from there and auto-registers if not already tracked.
    Falls back to default prompts/guides directory if neither is provided.
    """
    _track_guide_access_event(guide_name, guide_path, guide_hash)

    # 1. Try to load from spawn by hash if provided
    if guide_hash:
        content = get_guide_from_spawn(guide_hash)
        if content:
            _track_guide_loaded_event(guide_name, guide_hash, "spawn")
            return content

    # 2. If guide_path is provided, load from there and auto-register
    if guide_path:
        if not guide_path.exists():
            _track_guide_load_failed_event(guide_name, guide_path, "file_not_found")
            raise FileNotFoundError(f"Guide file not found: {guide_path}")
        content = guide_path.read_text()
        current_hash = sha256.hash_string(content)
        _auto_register_guide_if_needed(guide_name, content, current_hash)
        _track_guide_loaded_event(guide_name, current_hash, "file_path")
        return content

    # 3. Fallback to default prompts/guides directory
    default_guide_path = _prompts_guides_dir() / f"{guide_name}.md"
    if not default_guide_path.exists():
        _track_guide_load_failed_event(guide_name, default_guide_path, "default_file_not_found")
        raise FileNotFoundError(f"Guide file not found: {default_guide_path}")
    content = default_guide_path.read_text()
    current_hash = sha256.hash_string(content)
    _auto_register_guide_if_needed(guide_name, content, current_hash)
    _track_guide_loaded_event(guide_name, current_hash, "default_directory")
    return content


def track_guide_in_spawn(guide_hash: str, guide_content: str, guide_name: str):
    """Track a guide in the spawn, similar to constitutions."""
    spawn_api.add_constitution_version(
        name=guide_name, # Use the guide_name as the constitution name
        content=guide_content,
        change_description="Auto-tracked guide from file system",
        created_by="spawn_app",
    )
