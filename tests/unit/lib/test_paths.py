from pathlib import Path

from space.lib import paths


def test_space_root():
    assert paths.space_root() == Path.home() / "space"


def test_dot_space():
    assert paths.dot_space() == Path.home() / "space" / ".space"


def test_backup_root():
    assert paths.backup_root() == Path.home() / ".space"


def test_canon_path_from_config(mocker):
    mock_space_root = Path("/tmp/test_space")
    mocker.patch("space.lib.paths.space_root", return_value=mock_space_root)
    mocker.patch("space.lib.config.load_config", return_value={"canon_path": "my_canon_dir"})
    expected_path = mock_space_root / "my_canon_dir"
    assert paths.canon_path() == expected_path


def test_canon_path_default(mocker):
    mock_space_root = Path("/tmp/test_space_root")
    mocker.patch("space.lib.paths.space_root", return_value=mock_space_root)
    mocker.patch("space.lib.config.load_config", return_value={})
    expected_path = mock_space_root / "canon"
    assert paths.canon_path() == expected_path
