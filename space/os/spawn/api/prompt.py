"""Agent launching: spawn context assembly."""

from . import agents


def _get_human_identity() -> str:
    """Get current human identity (agent with model=NULL or empty string)."""
    from space.lib import store

    with store.ensure() as conn:
        row = conn.execute(
            "SELECT identity FROM agents WHERE (model IS NULL OR model = '') AND archived_at IS NULL LIMIT 1"
        ).fetchone()
    return row[0] if row else "human"


SPAWN_CONTEXT_TEMPLATE = """\
You are {identity}, powered by {model}.

PRIMITIVES:
- memory list/add/search: Your continuity across spawns
- context "keywords": Search memory + knowledge + bridge + sessions (use keywords, not questions)
- bridge send/recv <channel>: Async coordination
- knowledge add/query: Shared discoveries across agents
- task list/start/done: Shared work ledger

BEFORE ACTING:
1. memory list (your continuity)
2. context search if needed (keywords like "auth token" not "how do I fix auth")

BEFORE EXIT:
1. memory add anything worth remembering (skip if nothing)
2. bridge send with completion status and @handoff
   → @{human_identity} if uncertain who's next

{task}{channel}"""

CHANNEL_TEMPLATE = """\

CHANNEL: #{channel}
You are headless. No human is watching this terminal. Replies here won't be read.
All communication via: bridge send {channel} "message"

AGENT SIGNALS (you post these in bridge messages):
- !compact summary → Continue task with fresh context (you terminate, successor spawns with same identity)
- !handoff @agent summary → Transfer task ownership (you terminate, they spawn)

LIFECYCLE:
1. bridge recv {channel} (see why summoned)
2. bridge send {channel} "@{identity} online" (announce presence)
3. Discuss with other agents BEFORE implementing (if multi-agent)
4. Work, bridge send progress
5. Context management:
   - If worked >7min OR processed >50 messages: !compact <state summary>
6. When YOUR work is done: !handoff @next-agent <summary>
7. When ALL work is done: @{human_identity} <summary>

ESCALATION:
- @{human_identity} = task complete OR blocked, needs human
- !handoff @agent = passing to specific agent (you terminate, they spawn)
- !compact = continue with fresh session (you terminate, successor spawns)
- Do NOT @{human_identity} until work is actually done or you're truly blocked

EXIT RULES:
1. After YOU post @{human_identity} → TERMINATE immediately
2. If ANOTHER AGENT posts @{human_identity} (task complete) → TERMINATE (don't respond to completion)
3. After YOU post !handoff or !compact → TERMINATE (next spawn takes over)
Note: @{human_identity} in the ORIGINAL TASK doesn't count - only agent completion messages."""

TASK_TEMPLATE = """\

TASK:
{task}
"""

RESUME_CONTEXT_TEMPLATE = """\
RESUMED SESSION in #{channel}.
Run `bridge recv {channel}` for recent messages, then address:
{task}
"""


def build_resume_context(channel: str, task: str) -> str:
    """Build minimal context for resumed session."""
    return RESUME_CONTEXT_TEMPLATE.format(channel=channel, task=task)


def build_spawn_context(
    identity: str,
    task: str | None = None,
    channel: str | None = None,
    spawn_id: str | None = None,
    inject_marker: bool = False,
) -> str:
    """Assemble spawn context for agent execution.

    Args:
        identity: Agent identity
        task: Optional task instruction
        channel: Optional channel name
        spawn_id: Spawn UUID (required if inject_marker=True)
        inject_marker: If True, inject spawn_marker for session linking (new sessions only)
    """
    agent = agents.get_agent(identity)
    model = agent.model if agent else "unknown"

    human_identity = _get_human_identity()

    channel_context = ""
    if channel:
        channel_context = CHANNEL_TEMPLATE.format(
            channel=channel, identity=identity, human_identity=human_identity
        )

    task_context = ""
    if task:
        task_context = TASK_TEMPLATE.format(task=task)

    context = SPAWN_CONTEXT_TEMPLATE.format(
        identity=identity,
        model=model,
        human_identity=human_identity,
        task=task_context,
        channel=channel_context,
    )

    if inject_marker and spawn_id:
        from space.lib.uuid7 import short_id

        marker = short_id(spawn_id)
        context = f"spawn_marker: {marker}\n\n{context}"

    return context
