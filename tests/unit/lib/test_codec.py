"""Base64 encoding/decoding tests."""

import pytest

from space.lib.codec import decode_base64, encode_base64


def test_encode_basic():
    result = encode_base64("hello world")
    assert result == "aGVsbG8gd29ybGQ="


def test_encode_empty():
    result = encode_base64("")
    assert result == ""


def test_encode_unicode():
    result = encode_base64("café")
    decoded = decode_base64(result)
    assert decoded == "café"


def test_decode_basic():
    result = decode_base64("aGVsbG8gd29ybGQ=")
    assert result == "hello world"


def test_decode_empty():
    result = decode_base64("")
    assert result == ""


def test_decode_invalid_base64():
    with pytest.raises(ValueError, match="Invalid base64"):
        decode_base64("not valid base64!!!")


def test_decode_invalid_utf8():
    invalid_utf8_b64 = "//8="
    with pytest.raises(ValueError, match="Invalid base64"):
        decode_base64(invalid_utf8_b64)


def test_roundtrip():
    original = "The quick brown fox jumps over the lazy dog"
    encoded = encode_base64(original)
    decoded = decode_base64(encoded)
    assert decoded == original
