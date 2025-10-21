from pathlib import Path

from space.lib import paths


def test_space_root(monkeypatch):
    monkeypatch.delenv("SPACE_ROOT", raising=False)
    assert paths.space_root() == Path.home() / "space"


def test_dot_space(monkeypatch):
    monkeypatch.delenv("SPACE_ROOT", raising=False)
    monkeypatch.delenv("SPACE_DOT_SPACE", raising=False)
    assert paths.dot_space() == Path.home() / "space" / ".space"


def test_global_root(monkeypatch):
    monkeypatch.delenv("SPACE_GLOBAL_ROOT", raising=False)
    assert paths.global_root() == Path.home() / ".space"


def test_canon_path_from_config(mocker):
    mock_space_root = Path("/tmp/test_space")
    mocker.patch("space.lib.paths.space_root", return_value=mock_space_root)
    mocker.patch("space.config.load_config", return_value={"canon_path": "my_canon_dir"})
    expected_path = mock_space_root / "my_canon_dir"
    assert paths.canon_path() == expected_path


def test_canon_path_default(mocker):
    mock_space_root = Path("/tmp/test_space_root")
    mocker.patch("space.lib.paths.space_root", return_value=mock_space_root)
    mocker.patch("space.config.load_config", return_value={})
    expected_path = mock_space_root / "canon"
    assert paths.canon_path() == expected_path
