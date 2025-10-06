import pytest
import os
from unittest.mock import patch
from pathlib import Path

# Assuming config_loader.py will be in space/os/lib/
# and config.py will be in space/os/
from space.os.lib.config_loader import load_config
from space.os.config import DEFAULT_CONFIG

@pytest.fixture(autouse=True)
def cleanup_env_vars():
    # Clean up any SPACE_ related env vars before each test
    for key in list(os.environ.keys()):
        if key.startswith("SPACE_"):
            del os.environ[key]
    yield

@pytest.fixture
def mock_home_dir(tmp_path):
    # Create a temporary home directory
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    # Create the .space directory inside the mock home directory
    (home_dir / ".space").mkdir()
    return home_dir

@pytest.fixture
def mock_user_config_path(mock_home_dir):
    # Return the path to the config file within the mock home directory
    return mock_home_dir / ".space" / "config.py"

def test_load_config_defaults():
    """
    Test that load_config returns the default configuration when no overrides are present.
    """
    config = load_config()
    assert config == DEFAULT_CONFIG

def test_load_config_env_var_override(cleanup_env_vars):
    """
    Test that environment variables override default settings.
    """
    os.environ["SPACE_LOGGING_LEVEL"] = "DEBUG"
    config = load_config()
    expected_config = DEFAULT_CONFIG.copy()
    expected_config["logging_level"] = "DEBUG"
    assert config == expected_config

def test_load_config_env_var_override_non_existent_key(cleanup_env_vars):
    """
    Test that environment variables for non-existent keys are ignored.
    """
    os.environ["SPACE_NON_EXISTENT_KEY"] = "VALUE"
    config = load_config()
    assert config == DEFAULT_CONFIG

def test_load_config_user_file_override(mock_home_dir, mock_user_config_path):
    """
    Test that user config file overrides default settings.
    """
    with open(mock_user_config_path, "w") as f:
        f.write("USER_CONFIG = {\"logging_level\": \"DEBUG\", \"new_setting\": \"user_value\"}")

    with patch("os.path.expanduser", lambda p: str(mock_home_dir) if p == "~" else str(mock_home_dir / p[2:] if p.startswith("~/") else p)):
        config = load_config()

    expected_config = DEFAULT_CONFIG.copy()
    expected_config["logging_level"] = "DEBUG"
    expected_config["new_setting"] = "user_value"
    assert config == expected_config

def test_load_config_user_file_precedence(mock_home_dir, mock_user_config_path, cleanup_env_vars):
    """
    Test that user config file overrides environment variables.
    """
    os.environ["SPACE_LOGGING_LEVEL"] = "WARNING"
    with open(mock_user_config_path, "w") as f:
        f.write("USER_CONFIG = {\"logging_level\": \"ERROR\"}")

    with patch("os.path.expanduser", lambda p: str(mock_home_dir) if p == "~" else str(mock_home_dir / p[2:] if p.startswith("~/") else p)):
        config = load_config()

    expected_config = DEFAULT_CONFIG.copy()
    expected_config["logging_level"] = "ERROR"
    assert config == expected_config

def test_load_config_non_existent_user_file(mock_home_dir, mock_user_config_path):
    """
    Test that config loads correctly if user config file does not exist.
    """
    mock_user_config_path.unlink(missing_ok=True) # Ensure it doesn't exist
    with patch("os.path.expanduser", lambda p: str(mock_home_dir) if p == "~" else str(mock_home_dir / p[2:] if p.startswith("~/") else p)):
        config = load_config()
    assert config == DEFAULT_CONFIG

def test_load_config_malformed_user_file(mock_home_dir, mock_user_config_path):
    """
    Test that a malformed user config file does not crash the loader and defaults are used.
    """
    with open(mock_user_config_path, "w") as f:
        f.write("THIS IS NOT PYTHON SYNTAX")

    with patch("os.path.expanduser", lambda p: str(mock_home_dir) if p == "~" else str(mock_home_dir / p[2:] if p.startswith("~/") else p)):
        config = load_config()

    assert config == DEFAULT_CONFIG

def test_load_config_user_file_no_user_config_var(mock_home_dir, mock_user_config_path):
    """
    Test that a user config file without a USER_CONFIG variable does not crash the loader.
    """
    with open(mock_user_config_path, "w") as f:
        f.write("SOME_OTHER_VAR = 123")

    with patch("os.path.expanduser", lambda p: str(mock_home_dir) if p == "~" else str(mock_home_dir / p[2:] if p.startswith("~/") else p)):
        config = load_config()

    assert config == DEFAULT_CONFIG
