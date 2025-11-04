from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from space.core.models import SessionEvent


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

    def discover(self) -> list[dict]:
        """Discover provider sessions.

        Returns:
            List of {cli, session_id, file_path, created_at}
        """
        ...

    def ingest(self, session: dict, dest_dir: Path) -> bool:
        """Ingest one session: copy/convert to destination directory.

        Args:
            session: Session dict with keys: session_id, file_path, cli, etc.
            dest_dir: Destination directory (e.g., ~/.space/sessions/provider/)

        Returns:
            True if ingested successfully, False otherwise
        """
        ...

    def index(self, session_id: str) -> int:
        """Index one session into database.

        Args:
            session_id: Session ID to index

        Returns:
            Number of messages indexed
        """
        ...

    def parse(self, file_path: Path, from_offset: int = 0) -> "list[SessionEvent]":
        """Parse provider session file to unified event format.

        Extracts tool calls, tool results, text responses, and other execution events.

        Args:
            file_path: Path to session JSONL or JSON file
            from_offset: Byte offset or message index to start from

        Returns:
            List of SessionEvent objects in chronological order
        """
        ...

    def tokens(self, file_path: Path) -> tuple[int | None, int | None]:
        """Extract total input and output tokens from chat session.

        Args:
            file_path: Path to chat file (JSONL or JSON)

        Returns:
            Tuple of (input_tokens, output_tokens) or (None, None) if not available
        """
        ...

    def session_id(self, output: str) -> str | None:
        """Extract session_id from execution output.

        Provider-specific parsing of structured output (JSON/JSONL).

        Args:
            output: Raw stdout from execution

        Returns:
            session_id if found, None otherwise
        """
        ...
