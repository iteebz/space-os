import click
from pathlib import Path
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from space.os.lib import fs
from space.os.lib.config import load_config # Import load_config
from space.os.core.storage import Repo

# Load configuration
config = load_config()

# Define SPACE_DIR based on config, defaulting to project root/.space
_database_root_dir = config.get("database_root_dir")
if _database_root_dir:
    SPACE_DIR = Path(_database_root_dir).expanduser() # Expand ~ to home directory
else:
    SPACE_DIR = fs.root() / ".space"

class App:
    """
    The base class for all applications in the agent-space OS.
    """
    def __init__(self, name: str):
        self._name = name
        self._db_path = SPACE_DIR / "apps" / f"{name}.db" # App databases now in ~/.space/apps/{app_name}.db
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
        # Migrations are now handled by the Repository itself

    # New: Method to register and get repositories
    def register_repository(self, name: str, repo_class: type[Repo]):
        """Registers a repository class for this app."""
        # The Repository now derives its own paths, so we only need to pass the app_name
        self._repositories[name] = repo_class(self.name)

    @property
    def repositories(self):
        """Provides access to registered repository instances."""
        return self._repositories
