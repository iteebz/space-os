import typer

from space.os import knowledge, spawn


def fmt_entry_header(entry, agent_identity: str = None) -> str:
    mark_archived = " [ARCHIVED]" if entry.archived_at else ""
    mark_core = " ★" if entry.core else ""
    name = agent_identity or ""
    if name:
        name = f" by {name}"
    return f"[{entry.memory_id[-8:]}] {entry.topic}{name}{mark_archived}{mark_core}"


def _truncate_smartly(text: str, max_len: int = 150) -> tuple[str, bool]:
    """Truncate at sentence/paragraph boundary, return (truncated, was_truncated)."""
    if len(text) <= max_len:
        return text, False

    text = text[:max_len]

    for boundary in [". ", ".\n", "\n\n", "\n"]:
        idx = text.rfind(boundary)
        if idx > max_len * 0.6:
            return text[: idx + len(boundary)].rstrip(), True

    return text.rstrip() + "…", True


def show_memory_entry(entry, ctx_obj, related=None):
    agent = spawn.get_agent(entry.agent_id)
    agent_identity = agent.identity if agent else None
    typer.echo(fmt_entry_header(entry, agent_identity))
    typer.echo(f"Created: {entry.created_at}\n")
    typer.echo(f"{entry.message}\n")

    if related:
        typer.echo("─" * 60)
        typer.echo(f"Related nodes ({len(related)}):\n")
        for rel_entry, overlap in related:
            typer.echo(fmt_entry_header(rel_entry))
            typer.echo(f"  {overlap} keywords")
            typer.echo(f"  {rel_entry.message[:100]}\n")


def display_context(timeline, current_state):
    if any(current_state.values()):
        typer.echo("## RESULTS\n")

        _display_session_results(current_state.get("sessions", []))
        _display_memory_results(current_state.get("memory", []))
        _display_knowledge_results(current_state.get("knowledge", []))
        _display_bridge_results(current_state.get("bridge", []))
        _display_canon_results(current_state.get("canon", []))
    else:
        typer.echo("No context found")


def _display_session_results(sessions):
    """Display sessions grouped by user/agent, with smart truncation."""
    if not sessions:
        return

    typer.echo(f"SESSIONS ({len(sessions)})\n")

    user_msgs = [r for r in sessions if r.get("role") == "user"]
    agent_msgs = [r for r in sessions if r.get("role") != "user"]

    if user_msgs:
        typer.echo("You:")
        for r in user_msgs[:2]:
            ref = r.get("reference", "?")
            text, truncated = _truncate_smartly(r.get("text", ""), max_len=150)
            indicator = " […]" if truncated else ""
            typer.echo(f"  {text}{indicator}")
            typer.echo(f"  ref: {ref}\n")

    if agent_msgs:
        typer.echo("Agent:")
        for r in agent_msgs[:2]:
            cli = r.get("cli", "?")
            ref = r.get("reference", "?")
            text, truncated = _truncate_smartly(r.get("text", ""), max_len=150)
            indicator = " […]" if truncated else ""
            typer.echo(f"  [{cli}] {text}{indicator}")
            typer.echo(f"  ref: {ref}\n")

    typer.echo()


def _display_memory_results(memory):
    """Display memory entries."""
    if not memory:
        return

    typer.echo(f"MEMORY ({len(memory)})\n")
    for r in memory[:3]:
        topic = r.get("topic", "untitled")
        msg, truncated = _truncate_smartly(r.get("message", ""), max_len=150)
        indicator = " […]" if truncated else ""
        ref = r.get("reference", "?")
        typer.echo(f"  {topic}: {msg}{indicator}")
        typer.echo(f"  ref: {ref}\n")
    typer.echo()


def _display_knowledge_results(knowledge):
    """Display knowledge entries."""
    if not knowledge:
        return

    typer.echo(f"KNOWLEDGE ({len(knowledge)})\n")
    for r in knowledge[:3]:
        domain = r.get("domain", "unknown")
        content, truncated = _truncate_smartly(r.get("content", ""), max_len=150)
        indicator = " […]" if truncated else ""
        ref = r.get("reference", "?")
        typer.echo(f"  {domain}: {content}{indicator}")
        typer.echo(f"  ref: {ref}\n")
    typer.echo()


def _display_bridge_results(bridge):
    """Display bridge messages."""
    if not bridge:
        return

    typer.echo(f"BRIDGE ({len(bridge)})\n")
    for r in bridge[:3]:
        channel = r.get("channel", "unknown")
        content, truncated = _truncate_smartly(r.get("content", ""), max_len=150)
        indicator = " […]" if truncated else ""
        ref = r.get("reference", "?")
        typer.echo(f"  #{channel}: {content}{indicator}")
        typer.echo(f"  ref: {ref}\n")
    typer.echo()


def _display_canon_results(canon):
    """Display canon files."""
    if not canon:
        return

    typer.echo(f"CANON ({len(canon)})\n")
    for r in canon[:3]:
        path = r.get("path", "unknown")
        content, truncated = _truncate_smartly(r.get("content", ""), max_len=150)
        indicator = " […]" if truncated else ""
        ref = r.get("reference", "?")
        typer.echo(f"  {path}: {content}{indicator}")
        typer.echo(f"  ref: {ref}\n")
    typer.echo()


def show_context(identity: str):
    agent = spawn.get_agent(identity)
    if not agent:
        typer.echo(f"\nNo agent found for identity: {identity}")
        return
    agent_id = agent.agent_id

    knowledge_entries = knowledge.query_knowledge_by_agent(agent_id)
    if knowledge_entries:
        domains = {e.domain for e in knowledge_entries}
        typer.echo(
            f"\nKNOWLEDGE: {len(knowledge_entries)} entries across {', '.join(sorted(domains))}"
        )
