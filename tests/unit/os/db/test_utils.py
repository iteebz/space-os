"""Tests for space.db.utils."""

import sqlite3
from dataclasses import dataclass

from space.os.db.utils import from_row


@dataclass
class SimpleEntity:
    """Test dataclass for from_row conversion."""

    id: str
    name: str
    value: int


def test_from_row_basic():
    """Test basic row to dataclass conversion."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test (id TEXT, name TEXT, value INTEGER)")
    cursor.execute("INSERT INTO test VALUES (?, ?, ?)", ("1", "test", 42))

    row = cursor.execute("SELECT id, name, value FROM test").fetchone()
    entity = from_row(row, SimpleEntity)

    assert entity.id == "1"
    assert entity.name == "test"
    assert entity.value == 42


def test_from_row_partial_fields():
    """Test conversion when row has extra fields not in dataclass."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test (id TEXT, name TEXT, value INTEGER, extra TEXT)")
    cursor.execute("INSERT INTO test VALUES (?, ?, ?, ?)", ("1", "test", 42, "ignored"))

    row = cursor.execute("SELECT id, name, value, extra FROM test").fetchone()
    entity = from_row(row, SimpleEntity)

    assert entity.id == "1"
    assert entity.name == "test"
    assert entity.value == 42


def test_from_row_missing_optional_fields():
    """Test conversion with optional fields."""

    @dataclass
    class OptionalEntity:
        id: str
        name: str
        description: str | None = None

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test (id TEXT, name TEXT)")
    cursor.execute("INSERT INTO test VALUES (?, ?)", ("1", "test"))

    row = cursor.execute("SELECT id, name FROM test").fetchone()
    entity = from_row(row, OptionalEntity)

    assert entity.id == "1"
    assert entity.name == "test"
    assert entity.description is None
