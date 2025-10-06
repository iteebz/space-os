import click
from pathlib import Path
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from space.os.lib import fs
from space.os.core.storage import Storage
from space.os.db.migration_manager import apply_migrations # Import apply_migrations

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

    def ensure_db(self):
        """Create database if missing."""
        # Simply ensure the database file exists. Migrations will handle schema.
        # The act of connecting to sqlite3.connect(self.db_path) will create the file if it doesn't exist.
        # No need for an initializer here anymore.
        with sqlite3.connect(self.db_path) as conn:
            conn.commit() # Ensure the file is created and committed.

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
        A hook for the app to perform any necessary initialization.
        This now includes applying database migrations.
        This can be overridden by the subclass.
        """
        self.ensure_db() # Ensure the database file exists
        with self.get_db_connection() as conn:
            apply_migrations(self.name, conn) # Apply migrations for this app

    # New: Method to register and get repositories
    def register_repository(self, name: str, repo_class: type[Storage]):
        """Registers a repository class for this app."""
        self._repositories[name] = repo_class(self.db_path)

    @property
    def repositories(self):
        """Provides access to registered repository instances."""
        return self._repositories
