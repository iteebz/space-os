import base64
import binascii


def decode_base64(content: str) -> str:
    try:
        payload = base64.b64decode(content, validate=True)
        return payload.decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise ValueError("Invalid base64 payload") from exc


def encode_base64(content: str) -> str:
    return base64.b64encode(content.encode("utf-8")).decode("utf-8")


__all__ = ["decode_base64", "encode_base64"]
