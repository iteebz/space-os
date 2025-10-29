"""Generic storage abstraction - database registry and lifecycle management."""

from space.lib.store.core import Row, ensure, from_row
from space.lib.store.health import (
    check_backup_has_data,
    compare_snapshots,
    get_backup_stats,
)
from space.lib.store.registry import (
    _reset_for_testing,
    add_migrations,
    alias,
    close_all,
    register,
    registry,
)
from space.lib.store.sqlite import connect, resolve

__all__ = [
    "ensure",
    "from_row",
    "Row",
    "register",
    "alias",
    "add_migrations",
    "registry",
    "_reset_for_testing",
    "close_all",
    "connect",
    "resolve",
    "check_backup_has_data",
    "get_backup_stats",
    "compare_snapshots",
]
