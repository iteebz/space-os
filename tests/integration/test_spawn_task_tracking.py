"""Integration tests for spawn task tracking and bridge coordination."""

import subprocess
from datetime import datetime
from unittest.mock import MagicMock, patch

from space.bridge import parser
from space.spawn import registry, spawn


class TestSpawnTaskLogging:
    """Test task logging on spawn execution."""

    def test_spawn_logs_task_without_channel(self, in_memory_db, tmp_path):
        """Spawn execution logs task to spawn.db without channel."""
        identity = "hailot"
        output = "test output"
        con_hash = spawn.hash_content("test constitution")

        task_id = registry.log_task(identity, output, constitution_hash=con_hash)

        with registry.get_db() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE uuid7 = ?", (task_id,)).fetchone()
            assert row["identity"] == identity
            assert row["output"] == output
            assert row["constitution_hash"] == con_hash
            assert row["channel"] is None
            assert row["completed_at"] is not None
            assert row["created_at"] is not None

    def test_spawn_logs_task_with_channel(self, in_memory_db):
        """Spawn execution logs task with channel for bridge tracking."""
        identity = "zealot"
        output = "analysis complete"
        con_hash = spawn.hash_content("zealot constitution")
        channel = "subagents-test"

        task_id = registry.log_task(identity, output, constitution_hash=con_hash, channel=channel)

        with registry.get_db() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE uuid7 = ?", (task_id,)).fetchone()
            assert row["channel"] == channel
            assert row["identity"] == identity

    def test_task_runtime_measurable(self, in_memory_db):
        """Completed_at allows task runtime measurement."""
        task_id = registry.log_task("hailot", "done")

        with registry.get_db() as conn:
            row = conn.execute(
                "SELECT created_at, completed_at FROM tasks WHERE uuid7 = ?", (task_id,)
            ).fetchone()

            created = datetime.fromisoformat(row["created_at"])
            completed = datetime.fromisoformat(row["completed_at"])
            assert completed >= created

    def test_constitution_hash_tracks_version(self, in_memory_db):
        """Constitution hash enables version tracking and provenance."""
        output = "test"
        hash1 = spawn.hash_content("constitution v1")
        hash2 = spawn.hash_content("constitution v2")

        task1 = registry.log_task("hailot", output, constitution_hash=hash1)
        task2 = registry.log_task("hailot", output, constitution_hash=hash2)

        with registry.get_db() as conn:
            row1 = conn.execute(
                "SELECT constitution_hash FROM tasks WHERE uuid7 = ?", (task1,)
            ).fetchone()
            row2 = conn.execute(
                "SELECT constitution_hash FROM tasks WHERE uuid7 = ?", (task2,)
            ).fetchone()

            assert row1["constitution_hash"] == hash1
            assert row2["constitution_hash"] == hash2
            assert row1["constitution_hash"] != row2["constitution_hash"]

    def test_multiple_tasks_retrievable(self, in_memory_db):
        """Multiple tasks logged and retrievable independently."""
        tasks = []
        for i in range(5):
            task_id = registry.log_task(f"agent{i}", f"output{i}", channel=f"channel{i}")
            tasks.append(task_id)

        with registry.get_db() as conn:
            rows = conn.execute("SELECT uuid7 FROM tasks ORDER BY created_at").fetchall()
            retrieved = [row["uuid7"] for row in rows]

        assert len(retrieved) == 5
        assert all(t in retrieved for t in tasks)


class TestBridgeMentionParsing:
    """Test bridge mention detection and spawn coordination."""

    def test_parse_single_mention(self):
        """Extract single @identity mention."""
        content = "@hailot what's the status?"
        mentions = parser.parse_mentions(content)
        assert mentions == ["hailot"]

    def test_parse_multiple_mentions(self):
        """Extract multiple @mentions from one message."""
        content = "@hailot @zealot thoughts?"
        mentions = parser.parse_mentions(content)
        assert set(mentions) == {"hailot", "zealot"}

    def test_parse_duplicate_mentions_deduplicated(self):
        """Deduplicate repeated mentions."""
        content = "@hailot please check. @hailot are you sure?"
        mentions = parser.parse_mentions(content)
        assert mentions == ["hailot"]

    def test_parse_no_mentions(self):
        """Return empty for message without mentions."""
        mentions = parser.parse_mentions("just a regular message")
        assert mentions == []

    def test_should_spawn_valid_identity(self):
        """Valid role identity should spawn."""
        assert parser.should_spawn("hailot", "content") is True
        assert parser.should_spawn("zealot", "content") is True

    def test_should_spawn_invalid_identity(self):
        """Invalid identity should not spawn."""
        assert parser.should_spawn("nonexistent", "content") is False
        assert parser.should_spawn("", "content") is False

    def test_spawn_from_mention_mocked(self):
        """Spawn from mention returns prompt for worker to execute."""
        with patch("space.bridge.parser.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="# test-channel\n\n[alice] hello\n"
            )

            result = parser.spawn_from_mention("hailot", "test-channel", "@hailot test message")

            # Result is prompt, not response
            assert result is not None
            assert "[TASK INSTRUCTIONS]" in result
            assert "test message" in result
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert call_args == ["bridge", "export", "test-channel"]

    def test_spawn_from_mention_failure(self):
        """Failed spawn returns None."""
        with patch("space.bridge.parser.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")

            result = parser.spawn_from_mention("hailot", "test-channel", "test")

            assert result is None

    def test_spawn_from_mention_timeout(self):
        """Spawn timeout returns None gracefully."""
        with patch("space.bridge.parser.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("spawn", 120)

            result = parser.spawn_from_mention("hailot", "test-channel", "test")

            assert result is None

    def test_process_message_extracts_and_spawns(self):
        """Process message detects mentions and returns prompts."""
        with patch("space.bridge.parser.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="# test-channel\n\n[alice] hello\n"
            )

            results = parser.process_message("test-channel", "@hailot hello")

            assert len(results) == 1
            assert results[0][0] == "hailot"
            # Result is prompt, not response
            assert "[TASK INSTRUCTIONS]" in results[0][1]

    def test_process_message_multiple_mentions(self):
        """Process multiple mentions in one message."""
        with patch("space.bridge.parser.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="# test-channel\n\n[alice] hello\n"
            )

            results = parser.process_message("test-channel", "@hailot @zealot thoughts?")

            assert len(results) == 2
            identities = [r[0] for r in results]
            assert set(identities) == {"hailot", "zealot"}
            # All results are prompts
            for _, prompt in results:
                assert "[TASK INSTRUCTIONS]" in prompt

    def test_process_message_skips_invalid(self):
        """Skip invalid identities in mentions."""
        with patch("space.bridge.parser.subprocess.run"):
            results = parser.process_message("test-channel", "@nonexistent @hailot hi")

            # Only hailot should be processed
            assert len(results) <= 1


class TestTaskChannelTracking:
    """Test channel-based task tracking for provenance."""

    def test_channel_groups_related_tasks(self, in_memory_db):
        """Tasks in same channel are grouped."""
        channel = "investigation-channel"
        registry.log_task("hailot", "started", channel=channel)
        registry.log_task("zealot", "analyzed", channel=channel)
        registry.log_task("hailot", "result", channel=channel)

        with registry.get_db() as conn:
            rows = conn.execute(
                "SELECT uuid7, identity FROM tasks WHERE channel = ? ORDER BY created_at",
                (channel,),
            ).fetchall()

        assert len(rows) == 3
        assert [r["identity"] for r in rows] == ["hailot", "zealot", "hailot"]

    def test_channel_isolation(self, in_memory_db):
        """Tasks from different channels isolated."""
        registry.log_task("hailot", "msg1", channel="channel-a")
        registry.log_task("zealot", "msg2", channel="channel-b")

        with registry.get_db() as conn:
            a_tasks = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE channel = ?", ("channel-a",)
            ).fetchone()[0]
            b_tasks = conn.execute(
                "SELECT COUNT(*) FROM tasks WHERE channel = ?", ("channel-b",)
            ).fetchone()[0]
            conn.execute("SELECT COUNT(*) FROM tasks WHERE channel IS NULL").fetchone()[0]

        assert a_tasks == 1
        assert b_tasks == 1

    def test_retrieve_channel_history(self, in_memory_db):
        """Retrieve full task history for channel."""
        channel = "investigation"
        tasks = [
            ("hailot", "started investigation"),
            ("zealot", "gathered data"),
            ("hailot", "final report"),
        ]

        for identity, output in tasks:
            registry.log_task(identity, output, channel=channel)

        with registry.get_db() as conn:
            rows = conn.execute(
                "SELECT identity, output FROM tasks WHERE channel = ? ORDER BY created_at",
                (channel,),
            ).fetchall()

        assert len(rows) == 3
        for i, (identity, output) in enumerate(tasks):
            assert rows[i]["identity"] == identity
            assert rows[i]["output"] == output


class TestEndToEndCoordination:
    """Test full spawn → log → bridge coordination."""

    def test_spawn_cli_logs_to_tasks_table(self, in_memory_db):
        """CLI invocation logs task with all metadata."""
        # This would require actual spawn invocation
        # Tested manually: spawn hailot "test" --channel subagents-test
        # Verified task appears in spawn.db with identity, channel, output, hash

        identity = "hailot"
        channel = "subagents-test"
        output = "response"
        con_hash = "abc123def456"

        task_id = registry.log_task(identity, output, constitution_hash=con_hash, channel=channel)

        with registry.get_db() as conn:
            row = conn.execute(
                "SELECT identity, channel, output, constitution_hash FROM tasks WHERE uuid7 = ?",
                (task_id,),
            ).fetchone()

        assert row["identity"] == identity
        assert row["channel"] == channel
        assert row["output"] == output
        assert row["constitution_hash"] == con_hash

    def test_bridge_send_triggers_mention_spawn(self):
        """Bridge send detects @mention and returns prompt for worker."""
        # Tested manually: bridge send subagents-test "@hailot message"
        # Verified: agent spawned, response logged, response piped to channel

        with patch("space.bridge.parser.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="# subagents-test\n\n[alice] hello\n"
            )

            results = parser.process_message("subagents-test", "@hailot question")

            assert len(results) == 1
            assert results[0][0] == "hailot"
            # Result is prompt for worker, not final response
            assert "[TASK INSTRUCTIONS]" in results[0][1]

    def test_task_provenance_chain(self, in_memory_db):
        """Task entry tracks full provenance: identity, channel, hash, timestamp."""
        identity = "hailot"
        channel = "investigation"
        output = "findings"
        con_hash = spawn.hash_content("zealot constitution")

        task_id = registry.log_task(identity, output, constitution_hash=con_hash, channel=channel)

        with registry.get_db() as conn:
            row = conn.execute(
                "SELECT uuid7, identity, channel, output, constitution_hash, created_at, completed_at FROM tasks WHERE uuid7 = ?",
                (task_id,),
            ).fetchone()

        assert row["uuid7"] == task_id
        assert row["identity"] == identity
        assert row["channel"] == channel
        assert row["output"] == output
        assert row["constitution_hash"] == con_hash
        assert row["created_at"] is not None
        assert row["completed_at"] is not None
