from pathlib import Path

import pytest
from typer.testing import CliRunner

from space.memory import cli, db
from space.spawn import registry

runner = CliRunner()


def _add_summary(identity: str, message: str, monkeypatch, cwd: Path):
    """Helper to add/replace a summary via the CLI."""
    with monkeypatch.context() as m:
        m.chdir(cwd)
        result = runner.invoke(cli.app, ["summary", "--as", identity, message])
    assert result.exit_code == 0
    return result


def _get_latest_summary(identity: str):
    """Helper to get the latest summary directly from the DB."""
    entries = db.get_memories(identity, topic="summary", limit=1)
    return entries[0] if entries else None


@pytest.fixture(autouse=True)
def setup_memory_db(test_space):
    registry.init_db()
    db.connect()  # Ensure db is initialized for tests


def test_summaries_append(test_space, monkeypatch):
    registry.init_db()
    registry.ensure_agent("test-agent")

    _add_summary("test-agent", "First session summary", monkeypatch, test_space)
    _add_summary("test-agent", "Second session summary", monkeypatch, test_space)
    _add_summary("test-agent", "Third session summary", monkeypatch, test_space)

    summaries = db.get_memories("test-agent", topic="summary")
    assert len(summaries) == 3
    assert summaries[0].message == "Third session summary"
    assert summaries[1].message == "Second session summary"
    assert summaries[2].message == "First session summary"


def test_summaries_empty(test_space):
    registry.init_db()
    registry.ensure_agent("test-agent")

    summaries = db.get_memories("test-agent", topic="summary")
    assert summaries == []


def test_summary_ordering(test_space, monkeypatch):
    registry.init_db()
    agent_id = registry.ensure_agent("test-agent")

    # Use the CLI helper to add summaries
    _add_summary(agent_id, "Session 0", monkeypatch, test_space)
    _add_summary(agent_id, "Session 1", monkeypatch, test_space)
    _add_summary(agent_id, "Session 2", monkeypatch, test_space)
    _add_summary(agent_id, "Session 3", monkeypatch, test_space)
    _add_summary(agent_id, "Session 4", monkeypatch, test_space)

    summaries = db.get_memories("test-agent", topic="summary")
    created_times = [s.created_at for s in summaries]

    assert created_times == sorted(created_times, reverse=True)


def test_no_summary_exists(test_space, monkeypatch):
    with monkeypatch.context() as m:
        m.chdir(test_space)
        result = runner.invoke(cli.app, ["summary", "--as", "test-agent"])
    assert result.exit_code == 0
    assert "No summary found for test-agent." in result.stdout


def test_add_new_summary(test_space, monkeypatch):
    with monkeypatch.context() as m:
        m.chdir(test_space)
        result = runner.invoke(cli.app, ["summary", "--as", "test-agent", "First summary message."])
    assert result.exit_code == 0
    assert "Added summary for test-agent." in result.stdout

    summary = _get_latest_summary("test-agent")
    assert summary is not None
    assert summary.message == "First summary message."
    assert summary.topic == "summary"


def test_replace_existing_summary(test_space, monkeypatch):
    _add_summary("test-agent", "Original summary.", monkeypatch, test_space)
    original_summary = _get_latest_summary("test-agent")

    with monkeypatch.context() as m:
        m.chdir(test_space)
        result = runner.invoke(
            cli.app, ["summary", "--as", "test-agent", "Updated summary message."]
        )
    assert result.exit_code == 0
    assert "Replaced 1 entry(ies) with" in result.stdout

    updated_summary = _get_latest_summary("test-agent")
    assert updated_summary is not None
    assert updated_summary.message == "Updated summary message."
    assert updated_summary.memory_id != original_summary.memory_id

    chain = db.get_chain(updated_summary.memory_id)
    assert len(chain["predecessors"]) == 1
    assert chain["predecessors"][0].memory_id == original_summary.memory_id
    assert chain["predecessors"][0].archived_at is not None


def test_show_lineage(test_space, monkeypatch):
    _add_summary("test-agent", "Summary 1.", monkeypatch, test_space)
    _add_summary("test-agent", "Summary 2.", monkeypatch, test_space)
    _add_summary("test-agent", "Summary 3.", monkeypatch, test_space)

    with monkeypatch.context() as m:
        m.chdir(test_space)
        result = runner.invoke(cli.app, ["summary", "--as", "test-agent"])
    assert result.exit_code == 0
    assert "CURRENT: [summary]" in result.stdout
    assert "Summary 3." in result.stdout
    assert "SUPERSEDES:" in result.stdout
    assert "Summary 2." in result.stdout
    assert "Summary 1." in result.stdout
