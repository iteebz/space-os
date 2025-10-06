# This file defines the public API for the space.context module.

from .knowledge import (
    query as query_knowledge,
)
from .knowledge import (
    write as write_knowledge,
)
from .memory import (
    clear as clear_memory_entries,
)
from .memory import (
    delete as delete_memory_entry,
)
from .memory import (
    edit as edit_memory_entry,
)
from .memory import (
    memorize as add_memory_entry,
)
from .memory import (
    recall as get_memory_entries,
)

__all__ = [
    # Knowledge functions
    "write_knowledge",
    "query_knowledge",
    # Memory functions
    "add_memory_entry",
    "get_memory_entries",
    "edit_memory_entry",
    "delete_memory_entry",
    "clear_memory_entries",
]
