import pytest

from space.apps import example

def test_reverse_string_basic():
    """
    Tests the basic functionality of the reverse_string function.
    """
    assert example.reverse_string("hello") == "olleh"

def test_reverse_string_empty():
    """
    Tests reverse_string with an empty string.
    """
    assert example.reverse_string("") == ""

def test_reverse_string_palindrome():
    """
    Tests reverse_string with a palindrome string.
    """
    assert example.reverse_string("madam") == "madam"

def test_reverse_string_with_spaces():
    """
    Tests reverse_string with a string containing spaces.
    """
    assert example.reverse_string("hello world") == "dlrow olleh"
