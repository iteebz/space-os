"""Tests for MCP registry and configuration."""

import json
import tempfile
from pathlib import Path

import pytest

from space.lib.mcp import registry


@pytest.fixture
def tmp_mcp_file(monkeypatch):
    """Temporary MCP config file for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        mcp_file = Path(tmpdir) / "mcp.json"
        monkeypatch.setattr(registry, "MCP_FILE", mcp_file)
        yield mcp_file


def test_list_available_returns_dict(tmp_mcp_file):
    """Test that list_available returns available MCPs."""
    available = registry.list_available()
    assert isinstance(available, dict)
    assert "notion" in available
    assert available["notion"]["name"] == "notion"


def test_load_config_empty(tmp_mcp_file):
    """Test loading empty config returns empty dict."""
    config = registry.load_config()
    assert config == {}


def test_save_config_creates_file(tmp_mcp_file):
    """Test that save_config writes file."""
    test_config = {"test": {"enabled": True}}
    registry.save_config(test_config)
    assert tmp_mcp_file.exists()
    loaded = json.loads(tmp_mcp_file.read_text())
    assert loaded == test_config


def test_enable_mcp(tmp_mcp_file):
    """Test enabling an MCP."""
    registry.enable("notion")
    config = registry.load_config()
    assert "notion" in config
    assert config["notion"]["enabled"] is True


def test_enable_unknown_mcp_raises(tmp_mcp_file):
    """Test enabling unknown MCP raises ValueError."""
    with pytest.raises(ValueError, match="Unknown MCP"):
        registry.enable("unknown-mcp")


def test_disable_mcp(tmp_mcp_file):
    """Test disabling an MCP."""
    registry.enable("notion")
    registry.disable("notion")
    config = registry.load_config()
    assert config["notion"]["enabled"] is False


def test_set_env(tmp_mcp_file):
    """Test setting environment variables for MCP."""
    registry.enable("notion")
    registry.set_env("notion", NOTION_API_KEY="test-key", NOTION_DB_ID="test-id")
    config = registry.load_config()
    assert config["notion"]["env"]["NOTION_API_KEY"] == "test-key"
    assert config["notion"]["env"]["NOTION_DB_ID"] == "test-id"


def test_get_launch_config_returns_enabled_only(tmp_mcp_file):
    """Test that get_launch_config returns only enabled MCPs."""
    registry.enable("notion")
    registry.set_env("notion", NOTION_API_KEY="key", NOTION_DB_ID="id")
    launch_config = registry.get_launch_config()
    assert "notion" in launch_config
    assert launch_config["notion"]["enabled"] is True


def test_get_config_returns_mcp_config(tmp_mcp_file):
    """Test getting specific MCP config."""
    registry.enable("notion")
    registry.set_env("notion", NOTION_API_KEY="key", NOTION_DB_ID="id")
    config = registry.get_config("notion")
    assert config is not None
    assert config["env"]["NOTION_API_KEY"] == "key"


def test_get_config_missing_returns_none(tmp_mcp_file):
    """Test getting config for non-existent MCP returns None."""
    config = registry.get_config("unknown")
    assert config is None
