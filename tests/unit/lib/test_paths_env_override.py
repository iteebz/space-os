from pathlib import Path


def test_space_root_respects_env_var(monkeypatch):
    """SPACE_ROOT env var should override default ~/space path."""
    monkeypatch.setenv("SPACE_ROOT", "/custom/space")

    import importlib

    from space.lib import paths

    importlib.reload(paths)

    result = paths.space_root()
    assert result == Path("/custom/space")


def test_space_root_expands_user(monkeypatch):
    """SPACE_ROOT should expand leading tilde."""
    monkeypatch.setenv("SPACE_ROOT", "~/altspace")

    import importlib

    from space.lib import paths

    importlib.reload(paths)

    result = paths.space_root()
    assert result == Path.home() / "altspace"


def test_dot_space_respects_env_var(monkeypatch):
    """SPACE_DOT_SPACE env var should override dot-space path."""
    monkeypatch.setenv("SPACE_DOT_SPACE", "/opt/myspace/.space")

    import importlib

    from space.lib import paths

    importlib.reload(paths)

    result = paths.dot_space()
    expected = Path("/opt/myspace/.space")
    assert result == expected


def test_dot_space_falls_back_to_space_root(monkeypatch):
    """dot_space should inherit SPACE_ROOT when dedicated override absent."""
    monkeypatch.setenv("SPACE_ROOT", "/workspace/main")
    monkeypatch.delenv("SPACE_DOT_SPACE", raising=False)

    import importlib

    from space.lib import paths

    importlib.reload(paths)

    result = paths.dot_space()
    assert result == Path("/workspace/main/.space")


def test_global_root_respects_env_var(monkeypatch):
    """SPACE_GLOBAL_ROOT env var should override ~/.space path."""
    monkeypatch.setenv("SPACE_GLOBAL_ROOT", "/var/space/global")

    import importlib

    from space.lib import paths

    importlib.reload(paths)

    result = paths.global_root()
    assert result == Path("/var/space/global")


def test_base_path_parameter_takes_precedence(monkeypatch):
    """base_path parameter should take precedence over env vars."""
    from space.lib import paths

    base = Path("/explicit/base")
    monkeypatch.setenv("SPACE_ROOT", "/ignored/path")
    result = paths.space_root(base_path=base)
    expected = base / "space"
    assert result == expected
