"""Storage backend protocol - defines interface for all storage implementations."""

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Storage(Protocol):
    """Storage backend protocol for database operations.

    Enables pluggable implementations (SQLite now, cloud in future).
    Backend-agnostic: uses generic Connection and Row types.
    """

    def connect(self, db_path: str) -> Any:
        """Open connection to database."""
        ...

    def ensure_schema(
        self,
        db_path: str,
        schema: str,
        migrations: list[tuple[str, str | Callable]] | None = None,
    ) -> None:
        """Ensure schema exists and apply migrations."""
        ...

    def register(self, name: str, db_file: str, schema: str) -> None:
        """Register database in registry."""
        ...

    def migrations(self, name: str, migs: list[tuple[str, str | Callable]]) -> None:
        """Register migrations for database."""
        ...

    def ensure(self, name: str) -> Any:
        """Ensure registered database exists and return connection."""
        ...

    def migrate(self, conn: Any, migrations: list[tuple[str, str | Callable]]) -> None:
        """Apply migrations to connection."""
        ...
