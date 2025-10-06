import pytest

from space.lib import encoding


def test_b64_encoding_decoding_roundtrip():
    """Test that encoding and then decoding a string returns the original string."""
    original_string = "Hello, World! This is a test string."
    encoded = encoding.encode_b64(original_string)
    decoded = encoding.decode_b64(encoded)
    assert decoded == original_string


def test_b64_encoding_decoding_roundtrip_unicode():
    """Test that encoding and then decoding a unicode string returns the original string."""
    original_string = "你好，世界！"
    encoded = encoding.encode_b64(original_string)
    decoded = encoding.decode_b64(encoded)
    assert decoded == original_string


def test_decode_b64_invalid_input():
    """Test that decoding an invalid base64 string raises an exception."""
    with pytest.raises(Exception):
        encoding.decode_b64("this is not base64")


def test_sha256_hashing():
    """Test the sha256 hashing function."""
    content = "Hello, World!"
    full_hash = encoding.sha256(content)
    assert isinstance(full_hash, str)
    assert len(full_hash) == 64


def test_sha256_hashing_with_length():
    """Test the sha256 hashing function with a specified length."""
    content = "Hello, World!"
    truncated_hash = encoding.sha256(content, 16)
    assert isinstance(truncated_hash, str)
    assert len(truncated_hash) == 16
