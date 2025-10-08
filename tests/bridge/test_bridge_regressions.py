from typer.testing import CliRunner


def test_recv_updates_respects_bookmarks(bridge_workspace):
    from space.bridge import api
    from space.bridge.api import messages as coordination_messages
    from space.bridge.storage import db as bridge_db

    bridge_db.init_db()
    channel_id = api.create_channel("bookmark-channel")

    api.send_message(channel_id, "human", "first message")
    messages, unread_count, _, _ = coordination_messages.recv_updates(channel_id, "agent-a")
    assert [msg.content for msg in messages] == ["first message"]
    assert unread_count == 1

    api.send_message(channel_id, "human", "second message")
    messages, unread_count, _, _ = coordination_messages.recv_updates(channel_id, "agent-a")
    assert [msg.content for msg in messages] == ["second message"]
    assert unread_count == 1

    def test_backup_cli_imports_helper_module(bridge_workspace, tmp_path):
        from space.bridge import cli as bridge_cli

        runner = CliRunner()
        result = runner.invoke(bridge_cli.app, ["backup"])

        assert result.exit_code == 0
        assert result.output  # Check that some output is produced
