import hashlib

def sha256(content: str, length: int | None = None) -> str:
    """Calculates the SHA256 hash of the content and optionally truncates it.

    Args:
        content: The string content to hash.
        length: The desired length of the truncated hash. If None, returns the full SHA256 hash.

    Returns:
        The (truncated) SHA256 hash as a hexadecimal string.
    """
    full_hash = hashlib.sha256(content.encode()).hexdigest()
    if length is None:
        return full_hash
    return full_hash[:length]
