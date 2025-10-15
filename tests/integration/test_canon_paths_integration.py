import os
import tempfile
from pathlib import Path

import pytest
import yaml

from space.lib import paths


@pytest.fixture
def temp_workspace():
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "project"
        workspace.mkdir()
        (workspace / ".space").mkdir()
        yield workspace


def test_canon_path_with_configured_value(temp_workspace):
    configured_canon_dir = "my_custom_canon"
    config_dir = temp_workspace / ".space"
    config_file = config_dir / "config.yaml"
    config_data = {"canon_path": configured_canon_dir}
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    # Temporarily change the current working directory to the workspace
    original_cwd = os.getcwd()
    try:
        os.chdir(temp_workspace)
        expected_path = temp_workspace / ".space" / configured_canon_dir
        assert paths.canon_path().resolve() == expected_path.resolve()
    finally:
        os.chdir(original_cwd)


def test_canon_path_with_default_value(temp_workspace):
    config_dir = temp_workspace / ".space"
    config_file = config_dir / "config.yaml"
    config_data = {}
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    # Temporarily change the current working directory to the workspace
    original_cwd = os.getcwd()
    try:
        os.chdir(temp_workspace)
        expected_path = temp_workspace / ".space" / "canon"
        assert paths.canon_path().resolve() == expected_path.resolve()
    finally:
        os.chdir(original_cwd)
