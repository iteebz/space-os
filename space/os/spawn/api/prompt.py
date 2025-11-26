"""Agent launching: spawn context assembly."""

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
- memory list/add/search: Your continuity across spawns
- context "query": Search memory + knowledge + bridge + sessions
- bridge send/recv <channel>: Async coordination
- knowledge add/query: Shared discoveries across agents
- spawn agents/inspect: Discover other agents

BEFORE ACTING:
1. memory list (see your continuity)
2. context search if task needs prior knowledge

BEFORE EXIT:
1. memory add anything worth remembering (skip if nothing)
2. bridge send with completion status and @handoff
   → @{human_identity} if uncertain who's next

{task}{channel}{task_mode}"""

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
) -> str:
    """Assemble spawn context for agent execution."""
    agent = agents.get_agent(identity)
    model = agent.model if agent else "unknown"

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
        task=task_context,
        channel=channel_context,
        task_mode=task_mode_context,
    )
