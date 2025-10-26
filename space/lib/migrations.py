"""Migration file loader - converts numbered .sql files to migration tuples."""

from pathlib import Path


def load_migrations(module_path: str) -> list[tuple[str, str]]:
    """Load migrations from migrations/ directory.

    Reads numbered .sql files (001_*.sql, 002_*.sql, etc.) and returns
    as migration tuples (name, sql_content) in lexical order.

    Args:
        module_path: Module path like 'space.apps.chats' or 'space.os.spawn'

    Returns:
        List of (migration_name, sql_content) tuples
    """
    parts = module_path.split(".")
    module_dir = Path(__file__).parent.parent
    for part in parts[1:]:
        module_dir = module_dir / part
    migrations_dir = module_dir / "migrations"

    if not migrations_dir.exists():
        return []

    migrations = []
    for sql_file in sorted(migrations_dir.glob("*.sql")):
        name = sql_file.stem
        sql_content = sql_file.read_text()
        migrations.append((name, sql_content))

    return migrations
