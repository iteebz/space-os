"""A simple example app."""

def reverse_string(s: str) -> str:
    """Reverses a string."""
    return s[::-1]

__all__ = ["reverse_string"]