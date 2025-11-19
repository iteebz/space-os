"""Database connection management and utilities."""

from space.lib.store.connection import (
    Row,
    _reset_for_testing,
    close_all,
    database_exists,
    ensure,
    from_row,
    set_test_db_path,
)
from space.lib.store.health import (
    check_backup_has_data,
    compare_snapshots,
    get_backup_stats,
)
from space.lib.store.sqlite import connect, resolve

__all__ = [
    "ensure",
    "from_row",
    "Row",
    "database_exists",
    "_reset_for_testing",
    "set_test_db_path",
    "close_all",
    "connect",
    "resolve",
    "check_backup_has_data",
    "get_backup_stats",
    "compare_snapshots",
]
