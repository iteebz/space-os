import sys
from typing import cast
import click

from space.os.protocols import App
from .cli import memory_group
from .api import (
    add_memory_entry,
    get_memory_entries,
    edit_memory_entry,
    delete_memory_entry,
    clear_memory_entries,
)

__all__ = [
    "add_memory_entry",
    "get_memory_entries",
    "edit_memory_entry",
    "delete_memory_entry",
    "clear_memory_entries",
]

@property
def name(self) -> str:
    return "memory"

def cli_group(self) -> click.Group:
    return memory_group

# Explicitly declare conformance to the App protocol
cast(App, sys.modules[__name__])