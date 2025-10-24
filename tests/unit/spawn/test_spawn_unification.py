"""TDD tests for spawn unification (architectural fix).

Tests validate:
1. Spawn stays pure (identity + constitutions only, no tasks)
2. Tasks tracked in bridge.db (bridge owns lifecycle)
3. Context injection via --context flag
4. Full export for bridge spawns
5. Unified agent interface across Claude/Gemini/Codex
"""

from space.os.bridge import api as bridge_api
from space.os.bridge import db as bridge_db
from space.os.spawn import registry, spawn


class TestSpawnPurityAfterRefactor:
    """Spawn registry must own ONLY identity + constitutions."""

    def test_registry_has_no_tasks_table(self, test_space):
        """Spawn registry schema must not include tasks table."""
        with registry.get_db() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
            )
            assert cursor.fetchone() is None, "tasks table should not exist in spawn.db"

    def test_registry_has_agents_and_constitutions(self, test_space):
        """Spawn registry must have agents and constitutions tables."""
        with registry.get_db() as conn:
            tables = set()
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for row in cursor.fetchall():
                tables.add(row[0])
            assert "agents" in tables
            assert "constitutions" in tables

    def test_log_task_function_removed(self, test_space):
        """log_task() function must be removed from registry."""
        assert not hasattr(registry, "log_task"), (
            "registry.log_task() should be removed (tasks belong in bridge, not spawn)"
        )


class TestBridgeTaskTracking:
    """Bridge owns task lifecycle (pending → running → completed/failed/timeout)."""

    def test_bridge_tasks_table_exists(self, test_space):
        """Bridge.db must have tasks table."""
        conn = bridge_db.connect()
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
        assert cursor.fetchone() is not None, "tasks table must exist in bridge.db"
        conn.close()

    def test_bridge_tasks_table_schema(self, test_space):
        """Bridge tasks table must have correct schema."""
        conn = bridge_db.connect()
        cursor = conn.execute("PRAGMA table_info(tasks)")
        columns = {col[1] for col in cursor.fetchall()}

        required = {
            "uuid7",
            "channel_id",
            "identity",
            "status",
            "input",
            "output",
            "stderr",
            "started_at",
            "completed_at",
            "created_at",
        }
        assert required.issubset(columns), f"Missing columns: {required - columns}"
        conn.close()

    def test_create_task_pending_status(self, test_space):
        """Tasks start with pending status."""
        channel_id = bridge_api.create_channel("task-channel")

        conn = bridge_db.connect()
        task_id = "test-task-uuid7"
        now = "2025-10-24T12:00:00"

        conn.execute(
            """
            INSERT INTO tasks (uuid7, channel_id, identity, status, input, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (task_id, channel_id, "hailot", "pending", "test input", now),
        )
        conn.commit()

        row = conn.execute("SELECT status FROM tasks WHERE uuid7 = ?", (task_id,)).fetchone()
        assert row[0] == "pending"
        conn.close()

    def test_task_lifecycle_states(self, test_space):
        """Tasks must support all lifecycle states."""
        channel_id = bridge_api.create_channel("lifecycle-channel")
        conn = bridge_db.connect()

        states = ["pending", "running", "completed", "failed", "timeout"]
        for state in states:
            task_id = f"task-{state}"
            conn.execute(
                """
                INSERT INTO tasks (uuid7, channel_id, identity, status, created_at)
                VALUES (?, ?, ?, ?, datetime('now'))
                """,
                (task_id, channel_id, "hailot", state),
            )

        conn.commit()
        cursor = conn.execute("SELECT status FROM tasks ORDER BY status")
        found_states = [row[0] for row in cursor.fetchall()]
        assert found_states == sorted(states)
        conn.close()


class TestContextInjection:
    """Tasks accept context via --context flag."""

    def test_spawn_app_accepts_context_flag(self, test_space):
        """spawn/app.py must parse --context flag."""
        import inspect

        from space.os.spawn.app import _spawn_from_registry

        source = inspect.getsource(_spawn_from_registry)
        assert "--context" in source, "--context flag must be parsed in spawn app"
        assert "context =" in source, "context variable must be assigned"

    def test_context_prepended_to_task_prompt(self, test_space):
        """Task prompt must prepend context when --context provided."""
        import inspect

        from space.os.spawn.app import _spawn_from_registry

        source = inspect.getsource(_spawn_from_registry)
        # Verify context is combined with task
        assert "context + " in source or "context +" in source, (
            "context must be concatenated with task prompt"
        )


class TestFullExportForBridgeSpawns:
    """Bridge spawns must get FULL channel export (no artificial limits)."""

    def test_parser_uses_full_export(self, test_space):
        """bridge/parser.py must not limit export to 10 messages."""
        import inspect

        from space.os.bridge import parser

        source = inspect.getsource(parser.spawn_from_mention)
        # Should NOT have the 10-message limit logic
        assert "len(messages) > 10" not in source, "Should not limit to 10 messages"
        assert "messages[-10:]" not in source, "Should not slice to last 10 messages"


class TestUnifiedAgentInterface:
    """Claude, Gemini, Codex must have identical interface."""

    def test_all_agents_have_run_method(self, test_space):
        """All agent classes must have run(prompt) method."""
        from space.os.spawn.agents import claude, codex, gemini

        for agent_class in [claude.Claude, gemini.Gemini, codex.Codex]:
            assert hasattr(agent_class, "run"), f"{agent_class.__name__} missing run() method"

            # Verify method signature
            import inspect

            sig = inspect.signature(agent_class.run)
            assert "prompt" in sig.parameters or len(sig.parameters) >= 2, (
                f"{agent_class.__name__}.run() must accept prompt parameter"
            )

    def test_agents_delegate_to_lib_agents(self, test_space):
        """Spawn agents must delegate to lib_agents backend."""
        from space.os.spawn.agents import claude, codex, gemini

        for module_name, agent_class in [
            ("claude", claude.Claude),
            ("gemini", gemini.Gemini),
            ("codex", codex.Codex),
        ]:
            import inspect

            source = inspect.getsource(agent_class.run)
            assert f"lib_agents.{module_name}" in source or f"agents.{module_name}" in source, (
                f"{agent_class.__name__} must delegate to lib_agents.{module_name}"
            )


class TestWorkerTaskTracking:
    """Bridge worker must create and update task records."""

    def test_worker_creates_task_before_spawn(self, test_space):
        """Worker must create task record BEFORE spawning agent."""
        import inspect

        from space.os.bridge import worker

        source = inspect.getsource(worker.main)
        # Should call _create_task before subprocess.run
        create_idx = source.find("_create_task")
        run_idx = source.find("subprocess.run")

        assert create_idx != -1 and run_idx != -1, (
            "Worker must have both _create_task and subprocess.run"
        )
        assert create_idx < run_idx, "Task must be created BEFORE subprocess.run"

    def test_worker_tracks_started_and_completed_times(self, test_space):
        """Worker must update started_at and completed_at timestamps."""
        import inspect

        from space.os.bridge import worker

        source = inspect.getsource(worker._update_task_completion)
        assert "started_at" in source or "_update_task_status" in inspect.getsource(worker.main), (
            "Worker must track started_at time"
        )
        assert "completed_at" in source, "Worker must track completed_at time"


class TestBridgeTaskCommands:
    """bridge tasks list/logs/wait must exist."""

    def test_tasks_commands_module_exists(self, test_space):
        """bridge/commands/tasks.py must exist."""
        from space.os.bridge.commands import tasks

        assert hasattr(tasks, "app"), "tasks.py must have typer app"

    def test_tasks_list_command(self, test_space):
        """bridge tasks list command must exist."""
        import inspect

        from space.os.bridge.commands import tasks

        source = inspect.getsource(tasks)
        assert "@app.command()" in source, "tasks must have @app.command() decorators"
        assert "def list(" in source, "tasks must have list() command"

    def test_tasks_logs_command(self, test_space):
        """bridge tasks logs command must exist."""
        from space.os.bridge.commands import tasks

        assert hasattr(tasks, "logs"), "tasks module must have logs function"

    def test_tasks_wait_command(self, test_space):
        """bridge tasks wait command must exist."""
        from space.os.bridge.commands import tasks

        assert hasattr(tasks, "wait"), "tasks module must have wait function"

    def test_tasks_wired_to_bridge_app(self, test_space):
        """bridge app must register tasks command group."""
        import inspect

        from space.os.bridge import app as bridge_app

        source = inspect.getsource(bridge_app)
        assert "tasks_cmds" in source or "tasks as tasks_cmds" in source, (
            "bridge/app.py must import tasks commands"
        )
        assert "add_typer" in source and "tasks" in source, (
            "bridge/app.py must wire tasks command group"
        )


class TestNoRegressions:
    """Existing functionality must not break."""

    def test_constitution_storage_unchanged(self, test_space):
        """Constitution storage (content-addressable by hash) must work."""

        content = "Test constitution content"
        content_hash = spawn.hash_content(content)

        registry.save_constitution(content_hash, content)
        retrieved = registry.get_constitution(content_hash)

        assert retrieved == content, "Constitution storage must work unchanged"

    def test_agent_identity_creation_unchanged(self, test_space):
        """Agent identity creation/lookup must work."""
        agent_id = registry.ensure_agent("test-agent")
        retrieved_id = registry.get_agent_id("test-agent")

        assert agent_id == retrieved_id, "Agent identity lookup must work"

    def test_bridge_channels_unchanged(self, test_space):
        """Bridge channel creation/message sending must work."""
        channel_id = bridge_api.create_channel("test-channel")
        bridge_api.send_message(channel_id, "agent-a", "test message")

        messages = bridge_db.get_all_messages(channel_id)
        assert len(messages) == 1
        assert messages[0].content == "test message"
