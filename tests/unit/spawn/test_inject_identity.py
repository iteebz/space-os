from space.lib import paths
from space.spawn import registry, spawn


def test_inject_identity_basic(test_space):
    """Injects identity header and footer."""
    constitution = "# ZEALOT CONSTITUTION\nPurge bullshit."
    
    result = spawn.inject_identity(constitution, "zealot-1")
    
    assert result.startswith("You are now zealot-1.")
    assert "# ZEALOT CONSTITUTION" in result
    assert "Purge bullshit." in result
    assert "run `space` for commands" in result


def test_inject_identity_with_self_description(test_space):
    """Includes self-description when present."""
    registry.init_db()
    registry.set_self_description("zealot-1", "Skeptical cothinking partner")
    
    constitution = "# ZEALOT CONSTITUTION"
    result = spawn.inject_identity(constitution, "zealot-1")
    
    assert "You are now zealot-1." in result
    assert "Self: Skeptical cothinking partner" in result
    assert "# ZEALOT CONSTITUTION" in result


def test_inject_identity_with_model(test_space):
    """Includes model in header when provided."""
    constitution = "# ZEALOT CONSTITUTION"
    result = spawn.inject_identity(constitution, "zealot-1", model="claude-sonnet-4-5")
    
    assert result.startswith("You are now zealot-1 powered by claude-sonnet-4-5.")


def test_inject_identity_with_canon(test_space):
    """Injects canon before constitution."""
    canon_path = paths.canon_path()
    canon_path.parent.mkdir(parents=True, exist_ok=True)
    canon_path.write_text("# CANON\n1. Truth\n2. Speed\n3. Craft")
    
    constitution = "# ZEALOT CONSTITUTION\nPurge bullshit."
    result = spawn.inject_identity(constitution, "zealot-1")
    
    lines = result.split("\n")
    canon_idx = next(i for i, line in enumerate(lines) if "# CANON" in line)
    zealot_idx = next(i for i, line in enumerate(lines) if "# ZEALOT CONSTITUTION" in line)
    
    assert canon_idx < zealot_idx
    assert "1. Truth" in result
    assert "2. Speed" in result
    assert "3. Craft" in result


def test_inject_identity_assembly_order(test_space):
    """Verifies full assembly: header → canon → constitution → footer."""
    registry.init_db()
    registry.set_self_description("zealot-1", "Skeptical partner")
    
    canon_path = paths.canon_path()
    canon_path.parent.mkdir(parents=True, exist_ok=True)
    canon_path.write_text("# CANON\n1. Truth")
    
    constitution = "# CONSTITUTION\nCore rules."
    result = spawn.inject_identity(constitution, "zealot-1", model="claude-sonnet-4-5")
    
    lines = result.split("\n")
    
    header_idx = next(i for i, line in enumerate(lines) if "You are now zealot-1" in line)
    self_idx = next(i for i, line in enumerate(lines) if "Self: Skeptical partner" in line)
    canon_idx = next(i for i, line in enumerate(lines) if "# CANON" in line)
    const_idx = next(i for i, line in enumerate(lines) if "# CONSTITUTION" in line)
    footer_idx = next(i for i, line in enumerate(lines) if "run `space`" in line)
    
    assert header_idx < self_idx < canon_idx < const_idx < footer_idx
