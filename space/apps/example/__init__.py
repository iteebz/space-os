import sys
from typing import cast
import click

from space.os.protocols import App
from .api import reverse_string
from .cli import example_group

__all__ = ["reverse_string"]

@property
def name(self) -> str:
    return "example"

def cli_group(self) -> click.Group:
    return example_group

cast(App, sys.modules[__name__])
