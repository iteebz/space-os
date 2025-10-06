import base64


def decode_b64(encoded_string: str) -> str:
    """Decodes a base64 encoded string."""
    return base64.b64decode(encoded_string).decode("utf-8")


def encode_b64(decoded_string: str) -> str:
    """Encodes a string to base64."""
    return base64.b64encode(decoded_string.encode("utf-8")).decode("utf-8")
