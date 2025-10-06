import click
from pathlib import Path
from .lib.db_utils import database_path

class BaseApp:
    """
    The base class for all applications in the agent-space OS.
    """
    def __init__(self, name: str):
        self._name = name
        self._db_path = database_path(self.name)

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
        pass
