from pathlib import Path

import pytest
import yaml

from space.lib import paths


@pytest.fixture
def mock_home_dir(tmp_path):
    yield tmp_path


def test_canon_path_with_configured_value(mock_home_dir, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: mock_home_dir)
    configured_canon_dir = "my_custom_canon"

    # Create the necessary directory structure for the test
    space_root_dir = mock_home_dir / "space"
    space_root_dir.mkdir(parents=True, exist_ok=True)

    config_dir = space_root_dir / ".space"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_file = config_dir / "config.yaml"
    config_data = {"canon_path": configured_canon_dir}
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    expected_path = space_root_dir / configured_canon_dir
    assert paths.canon_path().resolve() == expected_path.resolve()


def test_canon_path_with_default_value(mock_home_dir, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: mock_home_dir)

    # Create the necessary directory structure for the test
    space_root_dir = mock_home_dir / "space"
    space_root_dir.mkdir(parents=True, exist_ok=True)

    config_dir = space_root_dir / ".space"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_file = config_dir / "config.yaml"
    config_data = {}
    with open(config_file, "w") as f:
        yaml.dump(config_data, f)

    expected_path = space_root_dir / "canon"
    assert paths.canon_path().resolve() == expected_path.resolve()
