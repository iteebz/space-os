from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Storage(Protocol):
    """Storage backend protocol."""

    def connect(self, db_path: str) -> Any: ...

    def ensure_schema(
        self,
        db_path: str,
        schema: str,
        migrations: list[tuple[str, str | Callable]] | None = None,
    ) -> None: ...

    def register(self, name: str, db_file: str, schema: str) -> None: ...

    def migrations(self, name: str, migs: list[tuple[str, str | Callable]]) -> None: ...

    def ensure(self, name: str) -> Any: ...

    def migrate(self, conn: Any, migrations: list[tuple[str, str | Callable]]) -> None: ...


@runtime_checkable
class Provider(Protocol):
    """LLM provider protocol (Claude, Codex, Gemini)."""

    def discover(self) -> list[dict]: ...

    def ingest(self, session: dict, dest_dir: Path) -> bool: ...

    def index(self, session_id: str) -> int: ...

    def parse(self, file_path: Path | str, from_offset: int = 0) -> "list[SessionMessage]": ...

    def tokens(self, file_path: Path) -> tuple[int | None, int | None]: ...

    def session_id_from_stream(self, output: str) -> str | None: ...

    def session_id_from_contents(self, file_path: Path) -> str | None: ...
