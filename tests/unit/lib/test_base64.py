import base64

import pytest

from space.lib.base64 import decode_base64_content, encode_base64_content


def test_encode_base64_content():
    test_string = "Hello, World!"
    encoded_string = encode_base64_content(test_string)
    assert encoded_string == base64.b64encode(test_string.encode("utf-8")).decode("utf-8")

    test_string_unicode = "你好，世界！"
    encoded_string_unicode = encode_base64_content(test_string_unicode)
    assert encoded_string_unicode == base64.b64encode(test_string_unicode.encode("utf-8")).decode(
        "utf-8"
    )


def test_decode_base64_content_valid():
    original_string = "Test string with some characters."
    encoded_string = base64.b64encode(original_string.encode("utf-8")).decode("utf-8")
    decoded_string = decode_base64_content(encoded_string)
    assert decoded_string == original_string

    original_string_unicode = "这是一个测试字符串。"
    encoded_string_unicode = base64.b64encode(original_string_unicode.encode("utf-8")).decode(
        "utf-8"
    )
    decoded_string_unicode = decode_base64_content(encoded_string_unicode)
    assert decoded_string_unicode == original_string_unicode


def test_decode_base64_content_invalid_base64():
    invalid_base64 = "This is not valid base64!"
    with pytest.raises(Exception) as excinfo:  # click.BadParameter is raised, which is an Exception
        decode_base64_content(invalid_base64)
    assert "Invalid base64 payload" in str(excinfo.value)


def test_decode_base64_content_invalid_utf8_after_base64():
    # This is a valid base64 string, but decodes to invalid UTF-8
    # For example, a byte sequence that is not a valid UTF-8 character
    # base64.b64encode(b'\x80').decode('utf-8') -> 'gA=='
    invalid_utf8_base64 = "gA=="  # This decodes to b'\x80' which is not valid UTF-8
    with pytest.raises(Exception) as excinfo:  # click.BadParameter is raised, which is an Exception
        decode_base64_content(invalid_utf8_base64)
    assert "Invalid base64 payload" in str(excinfo.value)


def test_base64_round_trip():
    original_string = "A string to be encoded and then decoded back."
    encoded = encode_base64_content(original_string)
    decoded = decode_base64_content(encoded)
    assert decoded == original_string

    original_string_with_special_chars = "Special chars: !@#$%^&*()_+-=[]{}|;':\",./<>?`~"
    encoded_special = encode_base64_content(original_string_with_special_chars)
    decoded_special = decode_base64_content(encoded_special)
    assert decoded_special == original_string_with_special_chars
