from space.lib import paths
from space.spawn import registry, spawn


def test_inject_self_description(test_space, mocker):
    """Includes self-description when present."""
    mocker.patch("space.lib.paths.space_root", return_value=test_space)
    registry.init_db()
    registry.set_self_description("zealot-1", "Skeptical cothinking partner")

    constitution = "# ZEALOT CONSTITUTION"
    result = spawn.inject_identity(constitution, "zealot", "zealot-1")

    assert "# ZEALOT CONSTITUTION" in result
    assert "Self: You are zealot-1." in result
    assert "# ZEALOT CONSTITUTION" in result


def test_inject_with_model(test_space, mocker):
    """Includes model in header when provided."""
    mocker.patch("space.lib.paths.space_root", return_value=test_space)
    constitution = "# ZEALOT CONSTITUTION"
    result = spawn.inject_identity(constitution, "zealot", "zealot-1", model="claude-sonnet-4-5")

    assert "# ZEALOT CONSTITUTION" in result
    assert "Self: You are zealot-1. Your model is claude-sonnet-4-5." in result


def test_inject_canon(test_space, mocker):
    """Injects canon before constitution."""
    mocker.patch("space.lib.paths.space_root", return_value=test_space)
    canon_path = paths.canon_path()
    canon_path.parent.mkdir(parents=True, exist_ok=True)
    canon_path.write_text("# CANON\n1. Truth\n2. Speed\n3. Craft")

    constitution = "# ZEALOT CONSTITUTION\nPurge bullshit."
    result = spawn.inject_identity(constitution, "zealot", "zealot-1")

    lines = result.split("\n")
    canon_idx = next(i for i, line in enumerate(lines) if "# CANON" in line)
    zealot_idx = next(i for i, line in enumerate(lines) if "# ZEALOT CONSTITUTION" in line)

    assert canon_idx > zealot_idx
    assert "1. Truth" in result
    assert "2. Speed" in result
    assert "3. Craft" in result


def test_inject_assembly_order(test_space, mocker):
    """Verifies full assembly: header → self → canon → constitution → footer."""
    mocker.patch("space.lib.paths.space_root", return_value=test_space)
    registry.init_db()
    registry.set_self_description("zealot-1", "Skeptical partner")

    canon_path = paths.canon_path()
    canon_path.parent.mkdir(parents=True, exist_ok=True)
    canon_path.write_text("# CANON\n1. Truth")

    constitution = "# CONSTITUTION\nCore rules."
    result = spawn.inject_identity(constitution, "zealot", "zealot-1", model="claude-sonnet-4-5")

    lines = result.split("\n")

    header_idx = next(i for i, line in enumerate(lines) if "# ZEALOT CONSTITUTION" in line)
    self_idx = next(
        i
        for i, line in enumerate(lines)
        if "Self: You are zealot-1. Your model is claude-sonnet-4-5." in line
    )
    canon_idx = next(i for i, line in enumerate(lines) if "# CANON" in line)
    const_idx = next(i for i, line in enumerate(lines) if "# CONSTITUTION" in line)
    footer_idx = next(
        i
        for i, line in enumerate(lines)
        if "run `space` for orientation (already in PATH)." in line
    )

    assert header_idx < self_idx < canon_idx < const_idx < footer_idx
