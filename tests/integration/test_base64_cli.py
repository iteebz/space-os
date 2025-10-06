import base64
import contextlib
import hashlib
from pathlib import Path

import pytest
from click.testing import CliRunner

from space.bridge import coordination
from space.bridge import storage as bridge_storage
from space.cli.bridge import bridge_group as bridge_cli_main
from space.cli.main import main as memory_cli_main
from space.lib.storage import context as context_db
from space.lib.storage import memory as memory_storage
from space.lib.storage import utils as storage
from space.spawn import config as spawn_config
from space.spawn import registry


# Fixture to set up a clean test environment for bridge commands
@pytest.fixture
def setup_bridge_env(monkeypatch):
    runner = CliRunner()
    with runner.isolated_filesystem() as fs:
        # Monkeypatch storage.database_path to use isolated filesystem
        def mock_database_path(name: str) -> Path:
            path = Path(fs) / ".space" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            return path

        monkeypatch.setattr(storage, "database_path", mock_database_path)

        # Ensure a clean database for each test
        bridge_storage.db.init_db()
        context_db.ensure()

        # Monkeypatch spawn config paths to use isolated filesystem
        spawn_dir_path = Path(fs) / ".space" / "spawn"
        registry_db_path = spawn_dir_path / "spawn.db"
        monkeypatch.setattr(spawn_config, "spawn_dir", lambda: spawn_dir_path)
        monkeypatch.setattr(spawn_config, "registry_db", lambda: registry_db_path)

        # Initialize spawn registry database in the isolated filesystem
        registry.init_db()

        # Define identity and channel for testing
        identity = "test-agent"
        channel_name = "test-channel"
        dummy_constitution_content = "This is a dummy constitution."
        dummy_constitution_hash = hashlib.sha256(dummy_constitution_content.encode()).hexdigest()
        registry.register(
            "test-role",
            identity,
            channel_name,
            identity_hash=dummy_constitution_hash,
            identity=dummy_constitution_content,
        )

        # Create a channel
        coordination.create_channel(channel_name)

        try:
            yield runner, identity, channel_name
        finally:
            # Teardown (cleanup is mostly handled by isolated_filesystem and init_db)
            with contextlib.suppress(ValueError):
                coordination.delete_channel(channel_name)
                registry.unregister(identity, channel_name)

# Fixture to set up a clean test environment for memory commands
@pytest.fixture
def setup_memory_env(monkeypatch):
    runner = CliRunner()
    with runner.isolated_filesystem() as fs:
        # Monkeypatch storage.database_path to use isolated filesystem
        def mock_database_path(name: str) -> Path:
            path = Path(fs) / ".space" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            return path

        monkeypatch.setattr(storage, "database_path", mock_database_path)
        # Ensure a clean database for each test by deleting the file if it exists
        db_path = storage.database_path(context_db.CONTEXT_DB_NAME)
        if db_path.exists():
            db_path.unlink()
        context_db.ensure()
        yield runner


# --- Bridge CLI Tests ---


def test_bridge_send_plain_text(setup_bridge_env):
    runner, identity, channel_name = setup_bridge_env
    message = "Hello, world!"
    result = runner.invoke(bridge_cli_main, ["send", channel_name, message, "--as", identity])
    print(result.output)
    print(result.exception)
    assert result.exit_code == 0
    assert "message_sent" in result.output
    # Verify message in DB (simplified check)
    messages = coordination.fetch_channel_messages(coordination.resolve_channel_id(channel_name))
    assert len(messages) == 1
    assert messages[0].content == message


def test_bridge_send_base64_encoded_text(setup_bridge_env):
    runner, identity, channel_name = setup_bridge_env
    original_message = "Hello, base64 world!"
    encoded_message = base64.b64encode(original_message.encode("utf-8")).decode("utf-8")
    result = runner.invoke(
        bridge_cli_main, ["send", channel_name, encoded_message, "--as", identity, "--base64"]
    )
    print(result.output)
    print(result.exception)
    assert result.exit_code == 0
    assert "message_sent" in result.output
    # Verify message in DB is decoded
    messages = coordination.fetch_channel_messages(coordination.resolve_channel_id(channel_name))
    assert len(messages) == 1
    assert messages[0].content == original_message


def test_bridge_send_invalid_base64(setup_bridge_env):
    runner, identity, channel_name = setup_bridge_env
    invalid_encoded_message = "This is not valid base64!"
    result = runner.invoke(
        bridge_cli_main,
        ["send", channel_name, invalid_encoded_message, "--as", identity, "--base64"],
    )
    assert result.exit_code != 0
    assert "Invalid base64 payload" in result.output


# --- Memory CLI Tests ---


def test_memory_add_plain_text(setup_memory_env):
    runner = setup_memory_env
    identity = "mem-agent"
    topic = "thoughts"
    message = "This is a plain text memory."
    result = runner.invoke(memory_cli_main, ["--as", identity, "--topic", topic, message])
    print(result.output)
    print(result.exception)
    assert result.exit_code == 0
    entries = memory_storage.get_entries(identity, topic)
    assert len(entries) == 1
    assert entries[0].message == message


def test_memory_add_base64_encoded_text(setup_memory_env):
    runner = setup_memory_env
    identity = "mem-agent"
    topic = "thoughts"
    original_message = "This is a base64 encoded memory."
    encoded_message = base64.b64encode(original_message.encode("utf-8")).decode("utf-8")
    result = runner.invoke(
        memory_cli_main, ["--as", identity, "--topic", topic, "--base64", encoded_message]
    )
    print(result.output)
    print(result.exception)
    assert result.exit_code == 0
    entries = memory_storage.get_entries(identity, topic)
    assert len(entries) == 1
    assert entries[0].message == original_message


def test_memory_add_invalid_base64(setup_memory_env):
    runner = setup_memory_env
    identity = "mem-agent"
    topic = "thoughts"
    invalid_encoded_message = "Not base64!"
    result = runner.invoke(
        memory_cli_main, ["--as", identity, "--topic", topic, "--base64", invalid_encoded_message]
    )
    assert result.exit_code != 0
    assert "Invalid base64 payload" in result.output


def test_memory_edit_plain_text(setup_memory_env):
    runner = setup_memory_env
    identity = "mem-agent"
    topic = "thoughts"
    initial_message = "Initial memory."
    result = runner.invoke(memory_cli_main, ["--as", identity, "--topic", topic, initial_message])
    print(result.output)
    print(result.exception)
    entry_uuid = memory_storage.get_entries(identity, topic)[0].uuid

    updated_message = "Updated plain text memory."
    result = runner.invoke(
        memory_cli_main,
        ["--as", identity, "--topic", topic, "--edit", str(entry_uuid), updated_message],
    )
    print(result.output)
    print(result.exception)
    assert result.exit_code == 0
    entries = memory_storage.get_entries(identity, topic)
    assert len(entries) == 1
    assert entries[0].message == updated_message


def test_memory_edit_base64_encoded_text(setup_memory_env):
    runner = setup_memory_env
    identity = "mem-agent"
    topic = "thoughts"
    initial_message = "Initial memory."
    result = runner.invoke(memory_cli_main, ["--as", identity, "--topic", topic, initial_message])
    print(result.output)
    print(result.exception)
    entry_uuid = memory_storage.get_entries(identity, topic)[0].uuid

    original_updated_message = "Updated base64 encoded memory."
    encoded_updated_message = base64.b64encode(original_updated_message.encode("utf-8")).decode(
        "utf-8"
    )
    result = runner.invoke(
        memory_cli_main,
        [
            "--as",
            identity,
            "--topic",
            topic,
            "--base64",
            "--edit",
            str(entry_uuid),
            encoded_updated_message,
        ],
    )
    print(result.output)
    print(result.exception)
    assert result.exit_code == 0
    entries = memory_storage.get_entries(identity, topic)
    assert len(entries) == 1
    assert entries[0].message == original_updated_message


def test_memory_edit_invalid_base64(setup_memory_env):
    runner = setup_memory_env
    identity = "mem-agent"
    topic = "thoughts"
    initial_message = "Initial memory."
    runner.invoke(memory_cli_main, ["--as", identity, "--topic", topic, initial_message])
    entry_uuid = memory_storage.get_entries(identity, topic)[0].uuid

    invalid_encoded_message = "Still not base64!"
    result = runner.invoke(
        memory_cli_main,
        [
            "--as",
            identity,
            "--topic",
            topic,
            "--base64",
            "--edit",
            str(entry_uuid),
            invalid_encoded_message,
        ],
    )
    assert result.exit_code != 0
    assert "Invalid base64 payload" in result.output


# --- Bridge Notes CLI Tests ---


def test_bridge_notes_add_plain_text(setup_bridge_env):
    runner, identity, channel_name = setup_bridge_env
    note_content = "This is a plain text note."
    result = runner.invoke(bridge_cli_main, ["notes", channel_name, note_content, "--as", identity])
    print(result.output)
    print(result.exception)
    assert result.exit_code == 0
    # Verify note in DB (simplified check)
    notes = coordination.get_notes(coordination.resolve_channel_id(channel_name))
    assert len(notes) == 1
    assert notes[0]["content"] == note_content


def test_bridge_notes_add_base64_encoded_text(setup_bridge_env):
    runner, identity, channel_name = setup_bridge_env
    original_note_content = "This is a base64 encoded note."
    encoded_note_content = base64.b64encode(original_note_content.encode("utf-8")).decode("utf-8")
    result = runner.invoke(
        bridge_cli_main, ["notes", channel_name, encoded_note_content, "--as", identity, "--base64"]
    )
    print(result.output)
    print(result.exception)
    assert result.exit_code == 0
    # Verify note in DB is decoded
    notes = coordination.get_notes(coordination.resolve_channel_id(channel_name))
    assert len(notes) == 1
    assert notes[0]["content"] == original_note_content


def test_bridge_notes_add_invalid_base64(setup_bridge_env):
    runner, identity, channel_name = setup_bridge_env
    invalid_encoded_note_content = "Bad base64 note!"
    result = runner.invoke(
        bridge_cli_main,
        ["notes", channel_name, invalid_encoded_note_content, "--as", identity, "--base64"],
    )
    print(result.output)
    print(result.exception)
    assert result.exit_code != 0
    assert "Invalid base64 payload" in result.output
