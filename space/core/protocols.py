"""Protocols defining interfaces for pluggable implementations."""

from collections.abc import Callable
from pathlib import Path
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


@runtime_checkable
class Provider(Protocol):
    """External LLM provider (Claude, Codex, Gemini).

    Unified interface for both chat discovery and agent spawning.
    """

    def discover_sessions(self) -> list[dict]:
        """Discover chat sessions.

        Returns:
            List of {cli, session_id, file_path, created_at}
        """
        ...

    def parse_messages(self, file_path: Path, from_offset: int = 0) -> list[dict]:
        """Parse messages from chat session file.

        Args:
            file_path: Path to chat file (JSONL or JSON)
            from_offset: Byte offset or message index to start from

        Returns:
            List of {role, content, timestamp, byte_offset/message_index}
        """
        ...

    def spawn(self, role: str, task: str | None = None) -> str:
        """Spawn agent instance with role.

        Args:
            role: Identity/role to spawn
            task: Optional task to execute

        Returns:
            Command output
        """
        ...

    def ping(self, identity: str) -> bool:
        """Check if agent is alive.

        Args:
            identity: Agent identity

        Returns:
            True if agent is responsive
        """
        ...

    def list_agents(self) -> list[str]:
        """List all active agents.

        Returns:
            List of agent identities
        """
        ...
