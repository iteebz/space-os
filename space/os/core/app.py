import click
from pathlib import Path
import sqlite3
from collections.abc import Iterator, Callable
from contextlib import contextmanager

from space.os.lib import fs
from space.os.core.storage import Storage

SPACE_DIR = fs.root() / ".space"

class App:
    """
    The base class for all applications in the agent-space OS.
    """
    def __init__(self, name: str):
        self._name = name
        self._db_path = SPACE_DIR / name
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._repositories = {} # New: To store repository instances

    @contextmanager
    def get_db_connection(self, row_factory: type | None = None) -> Iterator[sqlite3.Connection]:
        """Yield a connection to the app's dedicated database."""
        conn = sqlite3.connect(self.db_path)
        if row_factory is not None:
            conn.row_factory = row_factory
        try:
            yield conn
        finally:
            conn.close()

    def ensure_db(self, initializer: Callable[[sqlite3.Connection], None] | None = None):
        """Create database if missing and run optional initializer inside a transaction."""
        with sqlite3.connect(self.db_path) as conn:
            if initializer is not None:
                initializer(conn)
            conn.commit()

    @property
    def name(self) -> str:
        """The unique name of the application."""
        return self._name

    @property
    def db_path(self) -> Path:
        """The path to the application's dedicated database."""
        return self._db_path

    def cli_group(self) -> click.Group:
        """
        The click command group for this application.
        This should be implemented by the subclass.
        """
        raise NotImplementedError

    def initialize(self):
        """
        A hook for the app to perform any necessary initialization,
        such as creating database schemas.
        This can be overridden by the subclass.
        """
        self.ensure_db()

    # New: Method to register and get repositories
    def register_repository(self, name: str, repo_class: type[Storage]):
        """Registers a repository class for this app."""
        self._repositories[name] = repo_class(self.db_path)

    @property
    def repositories(self):
        """Provides access to registered repository instances."""
        return self._repositories
