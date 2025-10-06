import sys
from typing import cast
import click

from space.os.protocols import App
from .cli import spawn_group

@property
def name(self) -> str:
    return "spawn"

def cli_group(self) -> click.Group:
    return spawn_group

# Explicitly declare conformance to the App protocol
cast(App, sys.modules[__name__])