"""Agent launching: unified context injection and spawn context assembly."""

from space.os import memory

from . import agents


def _get_human_identity() -> str:
    """Get current human identity (agent with model=NULL)."""
    from space.lib import store

    with store.ensure() as conn:
        row = conn.execute("SELECT identity FROM agents WHERE model IS NULL LIMIT 1").fetchone()
    return row[0] if row else "human"


SPAWN_CONTEXT_TEMPLATE = """\
You are {identity}, powered by {model}.

PRIMITIVES:
- memory add "X" --topic <topic>: Persist learnings (observations, decisions, blockers, journal)
- bridge send/recv <channel>: Async coordination. All output MUST go through bridge, not stdout.
- knowledge add/query: Shared discoveries across agents
- context "query": Search across all primitives
- spawn agents/inspect: Discover other agents

BEFORE EXIT:
1. memory add anything worth remembering (skip if nothing)
2. bridge send with completion status and @handoff
   → @{human_identity} if uncertain who's next

{memories}{task}{channel}{task_mode}"""

MEMORIES_TEMPLATE = """\
YOUR CONTINUITY:
{memories_list}
"""

CHANNEL_TEMPLATE = """\

CHANNEL: #{channel}
Stdout goes nowhere. Use: bridge send {channel} "message"
First: bridge recv {channel} (see why you were summoned)
Then: acknowledge, work, handoff."""

TASK_TEMPLATE = """\

TASK:
{task}
"""

TASK_MODE_TEMPLATE = """\

MODE: Ephemeral (non-interactive). Complete task and exit."""


def build_spawn_context(
    identity: str,
    task: str | None = None,
    channel: str | None = None,
    is_ephemeral: bool = False,
    is_continue: bool = False,  # unused, kept for API compatibility
) -> str:
    """Assemble spawn context for agent execution."""
    agent = agents.get_agent(identity)
    agent_id = agent.agent_id if agent else None
    model = agent.model if agent else "unknown"

    memories_context = ""
    if agent_id:
        try:
            all_memories = memory.api.list_memories(identity, limit=20)
            if all_memories:
                mem_lines = []
                for e in all_memories:
                    marker = "★" if e.core else " "
                    topic_tag = f"[{e.topic}]" if e.topic else ""
                    mem_lines.append(f"  {marker} {topic_tag} {e.message}".strip())
                memories_context = MEMORIES_TEMPLATE.format(memories_list="\n".join(mem_lines))
        except Exception:
            pass

    channel_context = ""
    if channel:
        channel_context = CHANNEL_TEMPLATE.format(channel=channel)

    task_context = ""
    if task:
        task_context = TASK_TEMPLATE.format(task=task)

    task_mode_context = TASK_MODE_TEMPLATE if is_ephemeral else ""

    human_identity = _get_human_identity()

    return SPAWN_CONTEXT_TEMPLATE.format(
        identity=identity,
        model=model,
        human_identity=human_identity,
        memories=memories_context,
        task=task_context,
        channel=channel_context,
        task_mode=task_mode_context,
    )
