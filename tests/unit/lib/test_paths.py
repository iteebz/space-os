import tempfile
from pathlib import Path

from space.lib import paths


def test_workspace_root_finds_dotspace():
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


def test_workspace_root_fallback_to_cwd():
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


def test_space_root_finds_dotspace():
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


def test_space_root_fallback_to_home():
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
