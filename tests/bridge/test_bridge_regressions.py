import sys
from types import SimpleNamespace

from click.testing import CliRunner


def test_recv_updates_respects_bookmarks(bridge_workspace):
    from space.bridge import coordination
    from space.bridge.coordination import messages as coordination_messages
    from space.bridge.storage import db as bridge_db

    bridge_db.init_db()
    channel_id = coordination.create_channel("bookmark-channel")

    coordination.send_message(channel_id, "human", "first message")
    messages, unread_count, _, _ = coordination_messages.recv_updates(channel_id, "agent-a")
    assert [msg.content for msg in messages] == ["first message"]
    assert unread_count == 1

    coordination.send_message(channel_id, "human", "second message")
    messages, unread_count, _, _ = coordination_messages.recv_updates(channel_id, "agent-a")
    assert [msg.content for msg in messages] == ["second message"]
    assert unread_count == 1


def test_channel_instructions_return_locked_content(bridge_workspace):
    from space.bridge import coordination
    from space.bridge.storage import db as bridge_db

    bridge_db.init_db()
    channel_id = coordination.create_channel("instructions-channel")

    instructions = coordination.channel_instructions(channel_id)
    assert instructions is not None
    instruction_hash, content, notes = instructions
    assert len(instruction_hash) == 8
    assert content
    assert notes == "default"


def test_backup_cli_imports_helper_module(monkeypatch, bridge_workspace, tmp_path):
    from space.bridge import cli as bridge_cli

    backup_path = tmp_path / "bridge-backup"

    def fake_backup():
        return backup_path

    monkeypatch.setitem(
        sys.modules, "bridge.backup", SimpleNamespace(backup_bridge_data=fake_backup)
    )

    runner = CliRunner()
    result = runner.invoke(bridge_cli.main, ["backup"])

    assert result.exit_code == 0
    assert f"✅ Backup created: {backup_path}" in result.output
