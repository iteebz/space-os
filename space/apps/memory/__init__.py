from .app import memory_app as app
from .api import (
    add_memory_entry,
    get_memory_entries,
    edit_memory_entry,
    delete_memory_entry,
    clear_memory_entries,
    _set_memory_repo_instance # Import the setter function
)

_set_memory_repo_instance(app.repositories['memory']) # Set the repository instance for the API module

__all__ = [
    "add_memory_entry",
    "get_memory_entries",
    "edit_memory_entry",
    "delete_memory_entry",
    "clear_memory_entries",
    "app",
]