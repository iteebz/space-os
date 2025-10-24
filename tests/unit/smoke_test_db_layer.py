"""Smoke test: verify DB layer imports and paths don't crash."""


def test_bridge_db_imports():
    """Test bridge.db module can be imported and path() returns Path."""
    from space.os.bridge import db
    from pathlib import Path

    path = db.path()
    assert isinstance(path, Path)
    assert path.name == "bridge.db"


def test_spawn_db_imports():
    """Test spawn.db module can be imported and path() returns Path."""
    from space.os.spawn import db
    from pathlib import Path

    path = db.path()
    assert isinstance(path, Path)
    assert path.name == "spawn.db"


def test_bridge_db_connect():
    """Test bridge.db.connect() returns a registry connection."""
    from space.os.bridge import db

    conn = db.connect()
    assert conn is not None
    conn.close()


def test_spawn_db_connect():
    """Test spawn.db.connect() returns a registry connection."""
    from space.os.spawn import db

    conn = db.connect()
    assert conn is not None
    conn.close()
