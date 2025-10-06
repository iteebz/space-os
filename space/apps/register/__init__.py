import click
from .cli import register_group

# Make the public API from api.py available on the package level
from .api import (
    fetch_by_sender,
    track_constitution,
    get_constitution_content,
    link,
    list_constitutions,
)

__all__ = [
    "fetch_by_sender",
    "track_constitution",
    "get_constitution_content",
    "link",
    "list_constitutions",
]

@property
def name(self) -> str:
    return "register"

def cli_group(self) -> click.Group:
    return register_group
