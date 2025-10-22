"""Shared database utilities."""

from dataclasses import fields
from typing import Any, TypeVar

T = TypeVar("T")


def from_row(row: dict[str, Any] | Any, dataclass_type: type[T]) -> T:
    """Convert dict-like row to dataclass instance.

    Matches row keys to dataclass field names. Works with any dict-like object
    (sqlite3.Row, dict, etc.) allowing backend-agnostic conversions.
    """
    field_names = {f.name for f in fields(dataclass_type)}
    row_dict = dict(row) if not isinstance(row, dict) else row
    kwargs = {key: row_dict[key] for key in field_names if key in row_dict}
    return dataclass_type(**kwargs)
