"""Security tests for context search input validation."""

import pytest

from space.apps.context import db as context_db


def test_accept_normal_search():
    context_db._validate_search_term("test")


def test_accept_max_length():
    max_term = "x" * context_db._MAX_SEARCH_LEN
    context_db._validate_search_term(max_term)


def test_reject_oversized():
    oversized = "x" * (context_db._MAX_SEARCH_LEN + 1)
    with pytest.raises(ValueError, match="Search term too long"):
        context_db._validate_search_term(oversized)


def test_accept_empty():
    context_db._validate_search_term("")


def test_unicode_counts_toward_limit():
    unicode_term = "x" * (context_db._MAX_SEARCH_LEN - 10) + "🔒" * 100
    with pytest.raises(ValueError, match="Search term too long"):
        context_db._validate_search_term(unicode_term)


def test_regex_pattern_limited():
    pattern = "(" + "a" * 300 + ")*"
    with pytest.raises(ValueError, match="Search term too long"):
        context_db._validate_search_term(pattern)


def test_whitespace_counted():
    whitespace = " " * (context_db._MAX_SEARCH_LEN + 1)
    with pytest.raises(ValueError, match="Search term too long"):
        context_db._validate_search_term(whitespace)


def test_wildcard_within_limit():
    pattern = "%" * (context_db._MAX_SEARCH_LEN - 10)
    context_db._validate_search_term(pattern)


def test_wildcard_oversized_reject():
    pattern = "%" * (context_db._MAX_SEARCH_LEN + 1)
    with pytest.raises(ValueError, match="Search term too long"):
        context_db._validate_search_term(pattern)
