from typing import Protocol, runtime_checkable
import click

@runtime_checkable
class App(Protocol):
    """
    Protocol for a self-contained application module.
    Ensures that the module provides a discoverable Click CLI group
    and a way to identify itself.
    """

    @property
    def name(self) -> str:
        """The name of the application module."""
        ...

    def cli_group(self) -> click.Group:
        """
        Returns the Click Group object for this application module's CLI.
        This group should be defined in the module's cli.py.
        """
        ...
