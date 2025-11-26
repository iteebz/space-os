"""Identity resolution for CLI commands."""

import os


def resolve_identity(explicit: str | None) -> str | None:
    """Resolve identity from explicit arg or SPACE_IDENTITY env var."""
    return explicit or os.environ.get("SPACE_IDENTITY")


def require_identity(explicit: str | None) -> str:
    """Resolve identity, raising if not found."""
    identity = resolve_identity(explicit)
    if not identity:
        raise ValueError("Identity required: use --as or set SPACE_IDENTITY")
    return identity
