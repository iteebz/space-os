from pathlib import Path

from space.os import config, spawn


def test_constitution_injection(test_space):
    """Test that constitution injection properly formats role header."""
    base_content = "Test constitution content"
    injected = spawn.inject_role(base_content, "sentinel", "test-agent")

    assert "# SENTINEL CONSTITUTION" in injected
    assert "Self: You are test-agent." in injected
    assert base_content in injected
    assert "run `space` for orientation" in injected
    assert "run: `memory --as test-agent` to access memories." in injected


def test_constitution_injection_with_model(test_space):
    """Test that model is included when provided."""
    base_content = "Test constitution"
    injected = spawn.inject_role(base_content, "zealot", "zealot-v2", model="claude-3-sonnet")

    assert "Self: You are zealot-v2. Your model is claude-3-sonnet." in injected


def test_get_base_agent(test_space):
    """Test resolving base agent from role config."""
    config.init_config()

    base_agent = spawn.get_base_agent("sentinel")
    assert base_agent in ["claude", "gemini", "codex"]


def test_resolve_model_alias(test_space):
    """Test model alias resolution."""
    config.init_config()

    haiku = spawn.resolve_model_alias("haiku")
    sonnet = spawn.resolve_model_alias("sonnet")

    assert haiku
    assert sonnet
    assert haiku != sonnet


def test_get_constitution_path(test_space):
    """Test resolving constitution file path."""
    config.init_config()

    path = spawn.get_constitution_path("sentinel")
    assert isinstance(path, Path)
    assert path.name.endswith(".md")
