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

LIFECYCLE:
1. bridge recv {channel} (see why summoned)
2. bridge send {channel} "@{identity} online" (announce presence)
3. Discuss with other agents BEFORE implementing (if multi-agent)
4. Work, bridge send progress
5. When YOUR work is done: bridge handoff {channel} <next-agent> "summary"
6. When ALL work is done: bridge send {channel} "@human <summary>"

ESCALATION:
- @human = task complete OR blocked, needs human
- bridge handoff = passing to specific agent
- Do NOT @human until work is actually done or you're truly blocked

EXIT RULES:
1. After YOU post @human → TERMINATE immediately
2. If ANOTHER AGENT posts @human (task complete) → TERMINATE (don't respond to completion)
3. After YOU handoff to another agent → TERMINATE (your part done)
Note: @human in the ORIGINAL TASK doesn't count - only agent completion messages."""

TASK_TEMPLATE = """\

TASK:
{task}
"""


def build_spawn_context(
    identity: str,
    task: str | None = None,
    channel: str | None = None,
) -> str:
    """Assemble spawn context for agent execution."""
    agent = agents.get_agent(identity)
    model = agent.model if agent else "unknown"

    channel_context = ""
    if channel:
        channel_context = CHANNEL_TEMPLATE.format(channel=channel, identity=identity)

    task_context = ""
    if task:
        task_context = TASK_TEMPLATE.format(task=task)

    human_identity = _get_human_identity()

    return SPAWN_CONTEXT_TEMPLATE.format(
        identity=identity,
        model=model,
        human_identity=human_identity,
        task=task_context,
        channel=channel_context,
    )
