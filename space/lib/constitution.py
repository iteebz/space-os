"""Constitution file management for AI providers."""

from pathlib import Path


PROVIDER_MAP = {
    "claude": ("CLAUDE.md", ".claude"),
    "gemini": ("GEMINI.md", ".gemini"),
    "codex": ("AGENTS.md", ".codex"),
}


def write_constitution(provider: str, content: str) -> Path:
    """Write constitution to provider home dir.
    
    Args:
        provider: Provider name (claude, gemini, codex)
        content: Constitution text to write
        
    Returns:
        Path to written file
        
    Raises:
        ValueError: If provider is unknown
    """
    if provider not in PROVIDER_MAP:
        raise ValueError(f"Unknown provider: {provider}")
    
    filename, agent_dir = PROVIDER_MAP[provider]
    target = Path.home() / agent_dir / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    return target


def read_constitution(provider: str) -> str | None:
    """Read constitution from provider home dir.
    
    Args:
        provider: Provider name (claude, gemini, codex)
        
    Returns:
        Constitution text or None if file doesn't exist
        
    Raises:
        ValueError: If provider is unknown
    """
    if provider not in PROVIDER_MAP:
        raise ValueError(f"Unknown provider: {provider}")
    
    filename, agent_dir = PROVIDER_MAP[provider]
    target = Path.home() / agent_dir / filename
    return target.read_text() if target.exists() else None


def swap_constitution(provider: str, new_content: str) -> str:
    """Temporarily swap constitution content.
    
    Returns original content so it can be restored.
    
    Args:
        provider: Provider name (claude, gemini, codex)
        new_content: Constitution text to write
        
    Returns:
        Original constitution content (or empty string if none existed)
        
    Raises:
        ValueError: If provider is unknown
    """
    original = read_constitution(provider) or ""
    write_constitution(provider, new_content)
    return original


__all__ = [
    "write_constitution",
    "read_constitution",
    "swap_constitution",
    "PROVIDER_MAP",
]
