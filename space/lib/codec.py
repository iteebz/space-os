"""Codec utilities for encoding/decoding data."""

import base64
import binascii


def decode_base64(content: str) -> str:
    """Decode base64-encoded string to UTF-8.

    Args:
        content: Base64-encoded string.

    Returns:
        Decoded UTF-8 string.

    Raises:
        ValueError: If base64 payload is invalid or not valid UTF-8.
    """
    try:
        payload = base64.b64decode(content, validate=True)
        return payload.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise ValueError("Invalid base64 payload") from exc


def encode_base64(content: str) -> str:
    """Encode string to base64.

    Args:
        content: String to encode.

    Returns:
        Base64-encoded string.
    """
    return base64.b64encode(content.encode("utf-8")).decode("utf-8")


__all__ = ["decode_base64", "encode_base64"]
