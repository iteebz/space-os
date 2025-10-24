"""Security tests for context search input validation."""

import pytest

from space.apps.context import db as context_db


def test_short_search_accepted():
    """Accept normal search terms."""
    context_db._validate_search_term("test")


def test_max_length_accepted():
    """Accept search terms at maximum length."""
    max_term = "x" * context_db._MAX_SEARCH_LEN
    context_db._validate_search_term(max_term)


def test_oversized_search_rejected():
    """Reject oversized search terms."""
    oversized = "x" * (context_db._MAX_SEARCH_LEN + 1)
    with pytest.raises(ValueError, match="Search term too long"):
        context_db._validate_search_term(oversized)


def test_very_large_search_rejected():
    """Reject very large search terms (DoS prevention)."""
    huge = "x" * 10000
    with pytest.raises(ValueError, match="Search term too long"):
        context_db._validate_search_term(huge)


def test_empty_search_accepted():
    """Accept empty search terms."""
    context_db._validate_search_term("")


def test_error_message_informative():
    """Error includes max length and actual length."""
    oversized = "x" * 300
    with pytest.raises(ValueError, match=str(context_db._MAX_SEARCH_LEN)):
        context_db._validate_search_term(oversized)


def test_unicode_counts_toward_limit():
    """Unicode characters count toward length limit."""
    unicode_term = "x" * (context_db._MAX_SEARCH_LEN - 10) + "🔒" * 100
    with pytest.raises(ValueError, match="Search term too long"):
        context_db._validate_search_term(unicode_term)


def test_regex_pattern_length_limited():
    """Regex patterns subject to length limit."""
    pattern = "(" + "a" * 300 + ")*"
    with pytest.raises(ValueError, match="Search term too long"):
        context_db._validate_search_term(pattern)


def test_boundary_max_plus_one_rejected():
    """Boundary: max_length + 1 is rejected."""
    boundary = "x" * (context_db._MAX_SEARCH_LEN + 1)
    with pytest.raises(ValueError, match="Search term too long"):
        context_db._validate_search_term(boundary)


def test_boundary_max_accepted():
    """Boundary: exactly max_length is accepted."""
    boundary = "x" * context_db._MAX_SEARCH_LEN
    context_db._validate_search_term(boundary)


def test_whitespace_counted_toward_limit():
    """Whitespace counts toward length limit."""
    whitespace = " " * (context_db._MAX_SEARCH_LEN + 1)
    with pytest.raises(ValueError, match="Search term too long"):
        context_db._validate_search_term(whitespace)


def test_catastrophic_backtracking_pattern_limited():
    """Catastrophic backtracking patterns limited by length."""
    pattern = "(" * 128 + "a" * 128 + ")" * 128
    with pytest.raises(ValueError, match="Search term too long"):
        context_db._validate_search_term(pattern)


def test_exponential_backtracking_limited():
    """Exponential backtracking limited by length."""
    pattern = "(a+)+b" * 50
    if len(pattern) > context_db._MAX_SEARCH_LEN:
        with pytest.raises(ValueError, match="Search term too long"):
            context_db._validate_search_term(pattern)


def test_like_wildcard_alone_safe():
    """LIKE wildcard patterns safe (limited by length)."""
    pattern = "%" * (context_db._MAX_SEARCH_LEN - 10)
    context_db._validate_search_term(pattern)


def test_like_wildcard_oversized_rejected():
    """Oversized LIKE patterns rejected."""
    pattern = "%" * (context_db._MAX_SEARCH_LEN + 1)
    with pytest.raises(ValueError, match="Search term too long"):
        context_db._validate_search_term(pattern)


def test_max_length_is_defined():
    """Max search length constant exists."""
    assert context_db._MAX_SEARCH_LEN > 0


def test_max_length_reasonable():
    """Max length is not too restrictive."""
    assert context_db._MAX_SEARCH_LEN >= 100
