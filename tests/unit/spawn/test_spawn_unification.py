"""TDD tests for spawn task ownership (architectural fix).

Tests validate:
1. Spawn owns task lifecycle (identity + constitutions + tasks)
2. Bridge uses spawn task API (coordinator, not task owner)
3. Context injection via --context flag
4. Full export for bridge spawns
5. Unified agent interface across Claude/Gemini/Codex
"""

from space.os.bridge import api as bridge_api
from space.os.bridge import db as bridge_db
from space.os.spawn import registry, spawn


class TestSpawnTaskOwnership:
    """Spawn owns task table (not bridge)."""

    def test_registry_has_tasks_table(self, test_space):
        """Spawn registry schema must include tasks table."""
        registry.init_db()
        with registry.get_db() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'"
            )
            assert cursor.fetchone() is not None, "tasks table must exist in spawn.db"

    def test_registry_has_agents_constitutions_tasks(self, test_space):
        """Spawn registry must have agents, constitutions, and tasks tables."""
        registry.init_db()
        with registry.get_db() as conn:
            tables = set()
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            for row in cursor.fetchall():
                tables.add(row[0])
            assert "agents" in tables
            assert "constitutions" in tables
            assert "tasks" in tables

    def test_spawn_task_functions_exist(self, test_space):
        """registry must have task management functions."""
        assert hasattr(registry, "create_task")
        assert hasattr(registry, "get_task")
        assert hasattr(registry, "update_task")
        assert hasattr(registry, "list_tasks")


class TestSpawnTaskSchema:
    """Spawn tasks table has correct schema."""

    def test_spawn_tasks_table_schema(self, test_space):
        """Spawn tasks table must have required columns."""
        registry.init_db()
        with registry.get_db() as conn:
            cursor = conn.execute("PRAGMA table_info(tasks)")
            columns = {col[1] for col in cursor.fetchall()}

            required = {
                "id",
                "identity",
                "channel_id",
                "input",
                "output",
                "stderr",
                "status",
                "started_at",
                "completed_at",
                "created_at",
            }
            assert required.issubset(columns), f"Missing columns: {required - columns}"

    def test_task_lifecycle_states(self, test_space):
        """Tasks must support all lifecycle states."""
        registry.init_db()
        registry.ensure_agent("test-agent")

        states = ["pending", "running", "completed", "failed", "timeout"]
        for state in states:
            task_id = registry.create_task(identity="test-agent", input=f"task-{state}")
            registry.update_task(task_id, status=state)

        for state in states:
            tasks = registry.list_tasks(status=state)
            assert len(tasks) == 1
            assert tasks[0]["status"] == state


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
        assert "len(messages) > 10" not in source, "Should not limit to 10 messages"
        assert "messages[-10:]" not in source, "Should not slice to last 10 messages"


class TestUnifiedAgentInterface:
    """Claude, Gemini, Codex must have identical interface."""

    def test_all_agents_have_run_method(self, test_space):
        """All agent classes must have run(prompt) method."""
        from space.os.spawn.agents import claude, codex, gemini

        for agent_class in [claude.Claude, gemini.Gemini, codex.Codex]:
            assert hasattr(agent_class, "run"), f"{agent_class.__name__} missing run() method"

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


class TestWorkerUsesSpawnTaskAPI:
    """Bridge worker creates spawn tasks via spawn.registry API."""

    def test_worker_uses_spawn_registry(self, test_space):
        """Worker must use spawn.registry for task management."""
        import inspect

        from space.os.bridge import worker

        source = inspect.getsource(worker.main)
        assert "registry.create_task" in source, "Worker must call registry.create_task"
        assert "registry.update_task" in source, "Worker must call registry.update_task"

    def test_worker_creates_task_before_spawn(self, test_space):
        """Worker must create task record BEFORE spawning agent."""
        import inspect

        from space.os.bridge import worker

        source = inspect.getsource(worker.main)
        create_idx = source.find("registry.create_task")
        run_idx = source.find("subprocess.run")

        assert create_idx != -1 and run_idx != -1, (
            "Worker must have both create_task and subprocess.run"
        )
        assert create_idx < run_idx, "Task must be created BEFORE subprocess.run"

    def test_worker_tracks_lifecycle_states(self, test_space):
        """Worker must track task lifecycle via registry."""
        import inspect

        from space.os.bridge import worker

        source = inspect.getsource(worker.main)
        assert "running" in source, "Worker must set status=running"
        assert "completed" in source or "failed" in source, "Worker must set completion status"
        assert "completed_at=True" in source, "Worker must track completed_at"


class TestSpawnTaskCommands:
    """spawn tasks, logs commands must exist."""

    def test_spawn_tasks_command_exists(self, test_space):
        """spawn tasks command must exist."""
        from space.os.spawn import app

        assert hasattr(app, "tasks_cmd"), "spawn app must have tasks_cmd"

    def test_spawn_logs_command_exists(self, test_space):
        """spawn logs command must exist."""
        from space.os.spawn import app

        assert hasattr(app, "logs_cmd"), "spawn app must have logs_cmd"

    def test_tasks_module_has_functions(self, test_space):
        """spawn/commands/tasks.py must have task functions."""
        from space.os.spawn.commands import tasks

        assert hasattr(tasks, "tasks_cmd"), "tasks module must have tasks_cmd()"
        assert hasattr(tasks, "logs_cmd"), "tasks module must have logs_cmd()"


class TestNoRegressions:
    """Existing functionality must not break."""

    def test_constitution_storage_unchanged(self, test_space):
        """Constitution storage (content-addressable by hash) must work."""
        registry.init_db()
        content = "Test constitution content"
        content_hash = spawn.hash_content(content)

        registry.save_constitution(content_hash, content)
        retrieved = registry.get_constitution(content_hash)

        assert retrieved == content, "Constitution storage must work unchanged"

    def test_agent_identity_creation_unchanged(self, test_space):
        """Agent identity creation/lookup must work."""
        registry.init_db()
        agent_id = registry.ensure_agent("test-agent")
        retrieved_id = registry.get_agent_id("test-agent")

        assert agent_id == retrieved_id, "Agent identity lookup must work"

    def test_bridge_channels_unchanged(self, test_space):
        """Bridge channel creation/message sending must work."""
        bridge_db.connect()
        channel_id = bridge_api.create_channel("test-channel")
        bridge_api.send_message(channel_id, "agent-a", "test message")

        messages = bridge_db.get_all_messages(channel_id)
        assert len(messages) == 1
        assert messages[0].content == "test message"
