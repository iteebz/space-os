import hashlib

from space.lib.hashing import sha256


def test_sha256_full_hash():
    content = "test string"
    expected_hash = hashlib.sha256(content.encode()).hexdigest()
    assert sha256(content) == expected_hash


def test_sha256_truncated_hash_8_chars():
    content = "another test string"
    expected_hash = hashlib.sha256(content.encode()).hexdigest()[:8]
    assert sha256(content, 8) == expected_hash


def test_sha256_truncated_hash_16_chars():
    content = "yet another test string with more content"
    expected_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    assert sha256(content, 16) == expected_hash


def test_sha256_empty_string():
    content = ""
    expected_hash = hashlib.sha256(content.encode()).hexdigest()
    assert sha256(content) == expected_hash
    assert sha256(content, 8) == expected_hash[:8]


def test_sha256_unicode_content():
    content = "你好世界"
    expected_hash = hashlib.sha256(content.encode()).hexdigest()
    assert sha256(content) == expected_hash
    assert sha256(content, 10) == expected_hash[:10]
