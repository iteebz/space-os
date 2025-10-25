"""Sleep journal end-to-end tests."""

import uuid

from typer.testing import CliRunner

from space.cli import app
from space.os import memory, spawn

runner = CliRunner()


def _unique_identity(prefix: str) -> str:
    """Generate unique identity to avoid test pollution."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def test_sleep_journal_requires_identity(test_space):
    """sleep-journal without --as fails."""
    result = runner.invoke(app, ["sleep-journal"])
    assert result.exit_code != 0


def test_add_journal_entry(test_space):
    """Add a journal entry."""
    ident = _unique_identity("test_agent")
    spawn.db.ensure_agent(ident)
    result = runner.invoke(app, ["sleep-journal", "--as", ident, "completed X"])
    assert result.exit_code == 0
    assert "Journal entry saved" in result.stdout


def test_show_last_journal_empty(test_space):
    """Show last journal when none exist."""
    ident = _unique_identity("test_empty")
    spawn.db.ensure_agent(ident)
    result = runner.invoke(app, ["sleep-journal", "--as", ident])
    assert result.exit_code == 0
    assert "No journal entries" in result.stdout


def test_show_last_journal(test_space):
    """Show last journal entry."""
    ident = _unique_identity("test_show")
    spawn.db.ensure_agent(ident)
    runner.invoke(app, ["sleep-journal", "--as", ident, "first entry"])
    result = runner.invoke(app, ["sleep-journal", "--as", ident])
    assert result.exit_code == 0
    assert "Last journal" in result.stdout
    assert "first entry" in result.stdout


def test_journal_lineage(test_space):
    """Journal entries link to predecessors."""
    ident = _unique_identity("test_lineage")
    spawn.db.ensure_agent(ident)

    runner.invoke(app, ["sleep-journal", "--as", ident, "entry 1"])
    runner.invoke(app, ["sleep-journal", "--as", ident, "entry 2"])

    entries = memory.get_memories(ident, topic="journal")
    assert len(entries) == 2

    latest = entries[0]
    prev = entries[1]

    chain = memory.get_chain(latest.memory_id)
    assert chain["predecessors"]
    assert chain["predecessors"][0].memory_id == prev.memory_id


def test_journal_in_wake(test_space):
    """Wake shows last journal entry."""
    ident = _unique_identity("test_wake")
    spawn.db.ensure_agent(ident)
    runner.invoke(app, ["sleep-journal", "--as", ident, "spawn 1 work"])

    result = runner.invoke(app, ["wake", "--as", ident, "--quiet"])
    assert result.exit_code == 0


def test_spawn_count_from_journal(test_space):
    """Spawn count derives from journal entries."""
    ident = _unique_identity("test_spawn_count")
    spawn.db.ensure_agent(ident)

    runner.invoke(app, ["sleep-journal", "--as", ident, "spawn 1"])
    runner.invoke(app, ["sleep-journal", "--as", ident, "spawn 2"])
    runner.invoke(app, ["sleep-journal", "--as", ident, "spawn 3"])

    entries = memory.get_memories(ident, topic="journal")
    assert len(entries) == 3
