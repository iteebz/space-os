import tempfile
from pathlib import Path

from space.lib import paths


def test_workspace_root_finds_dot_space():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "project"
        workspace.mkdir()
        (workspace / ".space").mkdir()

        subdir = workspace / "nested" / "deep"
        subdir.mkdir(parents=True)

        import os

        orig_cwd = os.getcwd()
        try:
            os.chdir(subdir)
            assert paths.workspace_root().resolve() == workspace.resolve()
        finally:
            os.chdir(orig_cwd)


def test_workspace_root_fallback_cwd():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "no-dotspace"
        workspace.mkdir()

        import os

        orig_cwd = os.getcwd()
        try:
            os.chdir(workspace)
            assert paths.workspace_root().resolve() == workspace.resolve()
        finally:
            os.chdir(orig_cwd)


def test_space_root_finds_dot_space():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "project"
        workspace.mkdir()
        dotspace = workspace / ".space"
        dotspace.mkdir()

        subdir = workspace / "nested" / "deep"
        subdir.mkdir(parents=True)

        import os

        orig_cwd = os.getcwd()
        try:
            os.chdir(subdir)
            assert paths.space_root().resolve() == dotspace.resolve()
        finally:
            os.chdir(orig_cwd)


def test_space_root_fallback_home():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "no-dotspace"
        workspace.mkdir()

        import os

        orig_cwd = os.getcwd()
        try:
            os.chdir(workspace)
            assert paths.space_root() == Path.home() / ".space"
        finally:
            os.chdir(orig_cwd)


def test_canon_path_from_config(mocker):
    mocker.patch("space.lib.config.load_config", return_value={"canon_path": "my_canon_dir"})
    mocker.patch("space.lib.paths.workspace_root", return_value=Path("/tmp/test_workspace"))
    expected_path = Path("/tmp/test_workspace") / "my_canon_dir"
    assert paths.canon_path() == expected_path


def test_canon_path_default(mocker):
    mocker.patch("space.lib.config.load_config", return_value={})
    mocker.patch(
        "space.lib.paths.space_root", return_value=Path("/tmp/test_space_root")
    )  # Mock space_root
    expected_path = Path("/tmp/test_space_root") / "canon"
    assert paths.canon_path() == expected_path
