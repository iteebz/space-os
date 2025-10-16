from space.bridge import parser


def test_parse_mentions_single():
    """Extract single @mention."""
    content = "@hailot can you help?"
    mentions = parser.parse_mentions(content)
    assert mentions == ["hailot"]


def test_parse_mentions_multiple():
    """Extract multiple @mentions."""
    content = "@hailot @zealot what do you think?"
    mentions = parser.parse_mentions(content)
    assert set(mentions) == {"hailot", "zealot"}


def test_parse_mentions_no_duplicates():
    """Deduplicate mentions."""
    content = "@hailot please respond. @hailot are you there?"
    mentions = parser.parse_mentions(content)
    assert mentions == ["hailot"]


def test_parse_mentions_none():
    """No mentions in content."""
    content = "just a regular message"
    mentions = parser.parse_mentions(content)
    assert mentions == []


def test_should_spawn_valid_role():
    """Check valid role identity."""
    assert parser.should_spawn("hailot", "some content") is True
    assert parser.should_spawn("zealot", "some content") is True


def test_should_spawn_invalid_role():
    """Check invalid role identity."""
    assert parser.should_spawn("nonexistent", "some content") is False
    assert parser.should_spawn("", "some content") is False


def test_extract_mention_task_simple():
    """Extract task after @mention."""
    content = "@hailot do something"
    task = parser.extract_mention_task("hailot", content)
    assert task == "do something"


def test_extract_mention_task_with_newlines():
    """Extract task with newlines after @mention."""
    content = "@hailot\nanalyze this situation"
    task = parser.extract_mention_task("hailot", content)
    assert task == "analyze this situation"


def test_extract_mention_task_multiple_mentions():
    """Extract task stops at next @mention."""
    content = "@hailot do this @zealot do that"
    task = parser.extract_mention_task("hailot", content)
    assert task == "do this"
    task = parser.extract_mention_task("zealot", content)
    assert task == "do that"


def test_extract_mention_task_empty():
    """Mention with no task."""
    content = "@hailot"
    task = parser.extract_mention_task("hailot", content)
    assert task == ""


def test_extract_mention_task_not_found():
    """Identity not mentioned."""
    content = "@zealot do something"
    task = parser.extract_mention_task("hailot", content)
    assert task == ""
