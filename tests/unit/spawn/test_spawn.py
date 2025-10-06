from pathlib import Path
from unittest.mock import patch

import pytest
from space.registry.models import RegistryEntry
from space.spawn import spawn


@pytest.fixture
def mock_fs_root():
    with patch("space.lib.fs.root", return_value=Path("/mock/root")) as mock:
        yield mock


@pytest.fixture
def mock_sha256():
    with patch("space.lib.sha256.sha256", return_value="mock_hash") as mock:
        yield mock


@pytest.fixture
def mock_prompt_read():
    with patch("space.lib.prompt.read", return_value="mock_constitution_content") as mock:
        yield mock


@pytest.fixture
def mock_registry_db_track_constitution():
    with patch("space.registry.db.track_constitution") as mock:
        yield mock


@pytest.fixture
def mock_registry_link():
    with patch("space.registry.registry.link") as mock:
        yield mock


@pytest.fixture
def mock_registry_fetch_by_sender():
    with patch("space.registry.registry.fetch_by_sender") as mock:
        yield mock


@pytest.fixture
def mock_config_read():
    with patch("space.config.read") as mock:
        mock.return_value = {
            "agents": {"test_role": {"provider": "default_provider", "model": "default_model"}}
        }
        yield mock


def test_spawn_registers_agent_and_tracks_constitution(
    mock_fs_root,
    mock_sha256,
    mock_prompt_read,
    mock_registry_db_track_constitution,
    mock_registry_link,
    mock_registry_fetch_by_sender,
    mock_config_read,
):
    """Test that spawn correctly registers an agent and tracks its constitution."""
    role = "test_role"
    sender_id = "test_sender"
    topic = "test_topic"

    result = spawn(role, sender_id, topic)

    # Verify constitution path and content are read
    mock_fs_root.assert_called_once()
    mock_prompt_read.assert_called_once_with(
        Path("/mock/root/private/canon/constitutions/test_role.md")
    )
    mock_sha256.assert_called_once_with("mock_constitution_content")

    # Verify constitution is tracked in the registry DB
    mock_registry_db_track_constitution.assert_called_once_with(
        "mock_hash", "mock_constitution_content"
    )

    # Verify agent is linked in the registry
    mock_registry_link.assert_called_once_with(
        agent_id=sender_id,
        role=role,
        channels=[topic],
        constitution_hash="mock_hash",
        constitution_content="mock_constitution_content",
        provider="default_provider",
        model="default_model",
    )

    # Verify the returned dictionary
    assert result == {
        "agent_id": sender_id,
        "role": role,
        "topic": topic,
        "constitution_hash": "mock_hash",
    }


def test_spawn_gets_agent_config_from_file_if_exists(
    mock_fs_root,
    mock_sha256,
    mock_prompt_read,
    mock_registry_db_track_constitution,
    mock_registry_link,
    mock_registry_fetch_by_sender,
    mock_config_read,
):
    """Test that spawn prioritizes agent config from a file."""
    role = "test_role"
    sender_id = "test_sender"
    topic = "test_topic"

    # Mock agent config file existence and content
    with patch("pathlib.Path.exists", return_value=True):
        with patch(
            "pathlib.Path.read_text",
            return_value='{"provider": "file_provider", "model": "file_model"}',
        ):
            result = spawn(role, sender_id, topic)

        mock_registry_link.assert_called_once_with(
            agent_id=sender_id,
            role=role,
            channels=[topic],
            constitution_hash="mock_hash",
            constitution_content="mock_constitution_content",
            provider="file_provider",
            model="file_model",
        )


def test_spawn_gets_agent_config_from_registry_if_no_file(
    mock_fs_root,
    mock_sha256,
    mock_prompt_read,
    mock_registry_db_track_constitution,
    mock_registry_link,
    mock_registry_fetch_by_sender,
    mock_config_read,
):
    """Test that spawn gets agent config from registry if no file config exists."""
    role = "test_role"
    sender_id = "test_sender"
    topic = "test_topic"

    # Mock no agent config file, but a registry entry
    with patch("pathlib.Path.exists", return_value=False):
        mock_registry_fetch_by_sender.return_value = RegistryEntry(
            agent_id=sender_id,
            role=role,
            channels="[]",
            registered_at="",
            constitution_hash="",
            self_description="",
            provider="registry_provider",
            model="registry_model",
        )

        result = spawn(role, sender_id, topic)

        mock_registry_link.assert_called_once_with(
            agent_id=sender_id,
            role=role,
            channels=[topic],
            constitution_hash="mock_hash",
            constitution_content="mock_constitution_content",
            provider="registry_provider",
            model="registry_model",
        )


def test_spawn_gets_agent_config_from_defaults_if_no_file_or_registry(
    mock_fs_root,
    mock_sha256,
    mock_prompt_read,
    mock_registry_db_track_constitution,
    mock_registry_link,
    mock_registry_fetch_by_sender,
    mock_config_read,
):
    """Test that spawn gets agent config from defaults if no file or registry config exists."""
    role = "test_role"
    sender_id = "test_sender"
    topic = "test_topic"

    # Mock no agent config file and no registry entry
    with patch("pathlib.Path.exists", return_value=False):
        mock_registry_fetch_by_sender.return_value = None

        result = spawn(role, sender_id, topic)

        mock_registry_link.assert_called_once_with(
            agent_id=sender_id,
            role=role,
            channels=[topic],
            constitution_hash="mock_hash",
            constitution_content="mock_constitution_content",
            provider="default_provider",
            model="default_model",
        )
