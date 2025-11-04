from unittest.mock import MagicMock, patch

import pytest

from space.lib import paths, store
from space.os import bridge, spawn
from space.os.spawn import defaults as spawn_defaults


@pytest.fixture
def test_space(monkeypatch, tmp_path, request):
    """Isolated test database per test execution.

    Provides:
    - Temporary directory for workspace
    - Isolated tmp_path DB instead of real ~/.space/space.db
    - Fresh registry state (setup + teardown reset)
    - Monkeypatched paths module

    ALL tests using store.ensure() must accept this fixture to ensure isolation.
    """
    store._reset_for_testing()

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "AGENTS.md").write_text("test workspace")

    dot_space_dir = workspace / ".space"
    dot_space_dir.mkdir(parents=True, exist_ok=True)

    db_path = dot_space_dir / "space.db"
    if db_path.exists():
        db_path.unlink()

    monkeypatch.setattr(paths, "space_root", lambda: workspace)
    monkeypatch.setattr(paths, "dot_space", lambda: dot_space_dir)

    with store.ensure():
        pass

    yield workspace

    store._reset_for_testing()


@pytest.fixture
def populated_space(test_space):
    # Create dummy constitution files for default agents
    for identity in spawn_defaults.DEFAULT_AGENT_MODELS:
        constitution_path = test_space / f"{identity}.md"
        constitution_path.write_text(
            f"# {identity} Constitution\n\nThis is a dummy constitution for {identity}."
        )

    # Register default channels for tests
    bridge.api.channels.create_channel("ch-1")
    bridge.api.channels.create_channel("ch-spawn-test-123")
    return test_space


@pytest.fixture
def mock_db():
    """Mock db.ensure context manager for unit tests."""
    mock_conn = MagicMock()
    with patch("space.lib.store.ensure") as mock_ensure:
        mock_ensure.return_value.__enter__.return_value = mock_conn
        mock_ensure.return_value.__exit__.return_value = None
        yield mock_conn


def make_mock_row(data):
    """Create a mock database row object."""
    row = MagicMock()
    row.__getitem__ = lambda self, key: data[key]
    row.keys = lambda: data.keys()
    return row


@pytest.fixture
def default_agents(test_space):
    """Registers default agents for tests and returns their identities."""
    handles: dict[str, str] = {}
    for identity in spawn_defaults.DEFAULT_AGENT_MODELS:
        if spawn.get_agent(identity) is None:
            model = spawn_defaults.canonical_model(identity)
            spawn.register_agent(identity, model, f"{identity}.md")
        agent = spawn.get_agent(identity)
        if agent is not None:
            handles[identity] = agent.agent_id
    return handles
