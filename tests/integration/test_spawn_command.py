from pathlib import Path

import pytest

from space.os import config
from space.os.spawn import db as spawn_db
from space.os.spawn import spawn


def test_constitution_injection(test_space):
    """Test that constitution injection properly formats identity header."""
    base_content = "Test constitution content"
    injected = spawn.inject_identity(base_content, "sentinel", "test-identity")

    assert "# SENTINEL CONSTITUTION" in injected
    assert "Self: You are test-identity." in injected
    assert base_content in injected
    assert "run `space` for orientation" in injected
    assert "run: `memory --as test-identity` to access memories." in injected


def test_constitution_injection_with_model(test_space):
    """Test that model is included when provided."""
    base_content = "Test constitution"
    injected = spawn.inject_identity(base_content, "zealot", "zealot-v2", model="claude-3-sonnet")

    assert "Self: You are zealot-v2. Your model is claude-3-sonnet." in injected


def test_constitution_hash(test_space):
    """Test content hashing for constitution versioning."""
    content1 = "constitution v1"
    content2 = "constitution v2"

    hash1 = spawn.hash_content(content1)
    hash2 = spawn.hash_content(content2)

    assert hash1 != hash2
    assert len(hash1) == 64
    assert all(c in "0123456789abcdef" for c in hash1)


def test_save_and_load_constitution(test_space):
    """Test saving and loading constitutions by hash."""

    content = "Constitution for test agent"
    content_hash = spawn.hash_content(content)

    spawn_db.save_constitution(content_hash, content)
    loaded = spawn_db.get_constitution(content_hash)

    assert loaded == content


def test_constitution_idempotent_save(test_space):
    """Test that saving same constitution twice doesn't error."""

    content = "Test constitution"
    content_hash = spawn.hash_content(content)

    spawn_db.save_constitution(content_hash, content)
    spawn_db.save_constitution(content_hash, content)

    loaded = spawn_db.get_constitution(content_hash)
    assert loaded == content


def test_get_base_identity(test_space):
    """Test resolving base identity from role config."""
    config.init_config()

    base_id = spawn.get_base_identity("sentinel")
    assert base_id in ["claude", "gemini", "codex"]


def test_resolve_model_alias(test_space):
    """Test model alias resolution."""
    config.init_config()

    haiku = spawn.resolve_model_alias("haiku")
    sonnet = spawn.resolve_model_alias("sonnet")

    assert haiku
    assert sonnet
    assert haiku != sonnet


def test_parse_command_string():
    """Test command string parsing."""
    cmd = spawn._parse_command("python -m space.commands agent")
    assert cmd == ["python", "-m", "space.commands", "agent"]


def test_parse_command_list():
    """Test command list parsing."""
    cmd_list = ["python", "-m", "space"]
    cmd = spawn._parse_command(cmd_list)
    assert cmd == cmd_list


def test_parse_command_with_quotes():
    """Test command parsing with quoted arguments."""
    cmd = spawn._parse_command("python -c \"print('hello')\"")
    assert "python" in cmd
    assert len(cmd) >= 2


def test_parse_command_empty_raises():
    """Test that empty command raises error."""
    with pytest.raises(ValueError, match="Command cannot be empty"):
        spawn._parse_command("")

    with pytest.raises(ValueError, match="Command list cannot be empty"):
        spawn._parse_command([])


def test_virtualenv_bin_paths():
    """Test virtual environment bin path collection."""
    env = {"VIRTUAL_ENV": "/path/to/venv"}
    paths = spawn._virtualenv_bin_paths(env)

    assert "/path/to/venv/bin" in paths


def test_build_launch_env():
    """Test launch environment building removes poetry venv."""
    env = spawn._build_launch_env()

    assert "VIRTUAL_ENV" not in env
    assert "PATH" in env
    assert env["PATH"]


def test_get_constitution_path(test_space):
    """Test resolving constitution file path."""
    config.init_config()

    path = spawn.get_constitution_path("sentinel")
    assert isinstance(path, Path)
    assert path.name.endswith(".md")
