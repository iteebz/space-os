"""Agent launching: unified context injection and spawn context assembly."""

from datetime import datetime

from space.os import memory

from . import agents, sessions

SPAWN_CONTEXT_TEMPLATE = """\
You are {identity}.

{continuity}{protocol}{channel}{task}"""

CONTINUITY_TEMPLATE = """\
Spawn #{spawn_count}. {spawn_status}.
{memories}
"""

MEMORIES_TEMPLATE = """\
Core memories:
{core_memories}
"""

PROTOCOL_TEMPLATE = """\
SPACE-OS PROTOCOL:
- Manage your own memory. Decide signal from noise.
- Use 'memory add' to persist insights before context resets.
- Interleave tools as needed: bridge (read/write), memory, knowledge, context.
- Before you exit: memory journal --as {identity} to log your session.
- Coordinate major decisions through bridge. Never decide alone.

"""

CHANNEL_TEMPLATE = """\
CHANNEL CONTEXT:
You are responding in #{channel}.
First: run 'bridge recv {channel} --as {identity}' to load messages.

"""

TASK_TEMPLATE = """\
TASK:
{task}"""

INTERACTIVE_TEMPLATE = "Context loaded. Ready to work. What are we tackling?"


def build_spawn_context(identity: str, task: str | None = None, channel: str | None = None) -> str:
    """Assemble unified spawn context: identity + continuity + protocol + task/channel.

    Three modes:
    - Interactive (task=None, channel=None): "What are we tackling?"
    - Direct task (task="...", channel=None): Execute task instruction
    - Channel task (task="...", channel="..."): Respond in channel with context

    Args:
        identity: Agent identity
        task: Task instruction. None = interactive mode
        channel: Channel name if @mention spawn (optional)

    Returns:
        Complete prompt for agent execution
    """
    agent = agents.get_agent(identity)
    agent_id = agent.agent_id if agent else None

    continuity = ""
    if agent_id:
        try:
            spawn_count = sessions.get_spawn_count(agent_id)
        except Exception:
            spawn_count = 0

        spawn_status = "First spawn"
        try:
            last_journal = memory.api.list_memories(identity, topic="journal", limit=1)
            if last_journal:
                entry = last_journal[0]
                created_at = datetime.fromisoformat(entry.created_at)
                from space.lib.format import format_duration

                duration = format_duration((datetime.now() - created_at).total_seconds())
                spawn_status = f"Last session {duration} ago"
        except Exception:
            pass

        memories = ""
        try:
            core_entries = memory.api.list_memories(identity, filter="core")
            if core_entries:
                core_list = "\n".join([f"  - {e.message}" for e in core_entries[:3]])
                memories = MEMORIES_TEMPLATE.format(core_memories=core_list)
        except Exception:
            pass

        continuity = CONTINUITY_TEMPLATE.format(
            spawn_count=spawn_count + 1, spawn_status=spawn_status, memories=memories
        )

    protocol = PROTOCOL_TEMPLATE.format(identity=identity)

    channel_context = ""
    if channel:
        channel_context = CHANNEL_TEMPLATE.format(channel=channel, identity=identity)

    task_context = ""
    if task:
        task_context = TASK_TEMPLATE.format(task=task)
    else:
        task_context = INTERACTIVE_TEMPLATE

    return SPAWN_CONTEXT_TEMPLATE.format(
        identity=identity,
        continuity=continuity,
        protocol=protocol,
        channel=channel_context,
        task=task_context,
    )
