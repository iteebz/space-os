from space.lib import paths
from space.spawn import registry, spawn


def test_hailot_zealot_prompt_lookup(test_space, monkeypatch):
    """Test that hailot can find zealot.md in prompts/ subdirectory."""
    monkeypatch.setattr(paths, "space_root", lambda base_path=None: test_space)

    prompts_dir = test_space / "canon" / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
    zealot_content = "**YOU ARE NOW A ZEALOT.**\n\n## CORE PRINCIPLES\nHelpfulness = Skeptical cothinking partner."
    (prompts_dir / "zealot.md").write_text(zealot_content)

    monkeypatch.setattr(paths, "canon_path", lambda base_path=None: test_space / "canon")

    result_path = spawn.get_constitution_path("zealot")

    assert result_path.exists(), f"Constitution path {result_path} does not exist"
    assert result_path.read_text() == zealot_content


def test_inject_self_description(test_space, mocker):
    """Includes self-description when present."""
    mocker.patch("space.lib.paths.dot_space", return_value=test_space)
    registry.init_db()
    registry.set_self_description("zealot-1", "Skeptical cothinking partner")

    constitution = "# ZEALOT CONSTITUTION"
    result = spawn.inject_identity(constitution, "zealot", "zealot-1")

    assert "# ZEALOT CONSTITUTION" in result
    assert "Self: You are zealot-1." in result
    assert "# ZEALOT CONSTITUTION" in result


def test_inject_with_model(test_space, mocker):
    """Includes model in header when provided."""
    mocker.patch("space.lib.paths.dot_space", return_value=test_space)
    constitution = "# ZEALOT CONSTITUTION"
    result = spawn.inject_identity(constitution, "zealot", "zealot-1", model="claude-sonnet-4-5")

    assert "# ZEALOT CONSTITUTION" in result
    assert "Self: You are zealot-1. Your model is claude-sonnet-4-5." in result


def test_inject_canon(test_space, mocker):
    """Canon files not injected into constitution."""
    mocker.patch("space.lib.paths.dot_space", return_value=test_space)
    canon_dir = test_space / "canon"
    canon_dir.mkdir(parents=True, exist_ok=True)
    (canon_dir / "test_canon.md").write_text("# CANON\n1. Truth\n2. Speed\n3. Craft")
    mocker.patch("space.lib.paths.canon_path", return_value=canon_dir)

    constitution = "# ZEALOT CONSTITUTION\nPurge bullshit."
    result = spawn.inject_identity(constitution, "zealot", "zealot-1")

    assert "1. Truth" not in result
    assert "2. Speed" not in result
    assert "3. Craft" not in result


def test_inject_assembly_order(test_space, mocker):
    """Verifies full assembly: header → self → constitution → footer."""
    mocker.patch("space.lib.paths.dot_space", return_value=test_space)
    registry.init_db()
    registry.set_self_description("zealot-1", "Skeptical partner")

    constitution = "# CONSTITUTION\nCore rules."
    result = spawn.inject_identity(constitution, "zealot", "zealot-1", model="claude-sonnet-4-5")

    lines = result.split("\n")

    header_idx = next(i for i, line in enumerate(lines) if "# ZEALOT CONSTITUTION" in line)
    self_idx = next(
        i
        for i, line in enumerate(lines)
        if "Self: You are zealot-1. Your model is claude-sonnet-4-5." in line
    )
    const_idx = next(i for i, line in enumerate(lines) if "# CONSTITUTION" in line)
    footer_idx = next(
        i
        for i, line in enumerate(lines)
        if "run `space` for orientation (already in PATH)." in line
    )

    assert header_idx < self_idx < const_idx < footer_idx
