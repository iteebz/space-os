from space.lib import canon, paths


def test_load_canon_when_missing(test_space):
    """Returns None when canon.md doesn't exist."""
    assert canon.load_canon() is None


def test_load_canon_when_exists(test_space):
    """Loads canon.md content."""
    canon_path = paths.canon_path()
    canon_path.parent.mkdir(parents=True, exist_ok=True)
    canon_path.write_text("# My Values\n1. Truth\n2. Speed\n3. Craft")

    result = canon.load_canon()
    assert result == "# My Values\n1. Truth\n2. Speed\n3. Craft"


def test_inject_canon_when_missing(test_space):
    """Returns constitution unchanged when canon missing."""
    constitution = "You are a zealot."
    assert canon.inject_canon(constitution) == constitution


def test_inject_canon_when_exists(test_space):
    """Injects canon at top of constitution."""
    canon_path = paths.canon_path()
    canon_path.parent.mkdir(parents=True, exist_ok=True)
    canon_path.write_text("# CANON\n1. Truth\n2. Speed\n3. Craft")

    constitution = "You are a zealot."
    result = canon.inject_canon(constitution)

    assert result == "# CANON\n1. Truth\n2. Speed\n3. Craft\n\nYou are a zealot."


def test_init_canon_creates_default(test_space):
    """Creates default canon.md template."""
    canon.init_canon()

    canon_path = paths.canon_path()
    assert canon_path.exists()

    content = canon_path.read_text()
    assert "# CANON" in content
    assert "My three core values" in content
    assert "[First value" in content


def test_init_canon_doesnt_overwrite(test_space):
    """Doesn't overwrite existing canon.md."""
    canon_path = paths.canon_path()
    canon_path.parent.mkdir(parents=True, exist_ok=True)
    canon_path.write_text("Custom canon")

    canon.init_canon()

    assert canon_path.read_text() == "Custom canon"
