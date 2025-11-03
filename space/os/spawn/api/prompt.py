"""Agent launching: unified context injection and spawn context assembly."""

from space.os import memory

from . import agents

SPAWN_CONTEXT_TEMPLATE = """\
You are {identity}.

PRIMITIVES (actual API with examples):
- memory add/list/search/core/inspect/archive: Working memory organized by --topic.
  → memory add "resolved X via Y approach" --topic observations
- bridge send/recv/wait: Immutable async coordination on named channels.
  → bridge send general "here's my thinking on X"
  → bridge recv general  (read others' thinking before deciding)
- knowledge add/search: Shared discoveries persisted and queryable.
- context search: Unified search across memory, knowledge, bridge, chats, canon.
  → context search "precedent for X pattern" --as {identity}

AGENT DISCOVERY:
→ spawn agents  (see all agents, their roles, and what they do)
→ spawn inspect <agent-name>  (see full details)

DECISION TREE:
WHEN STUCK → spawn agents to find the right agent, then bridge send @agent_name
WHEN LEARNING → memory add "insight" --topic observations
WHEN SESSION DONE → memory add "session summary" --topic journal

Your responsibility: bridge to other agents, manage your memory, learn from interactions.

{memories}{task}{channel}"""

MEMORIES_TEMPLATE = """\
YOUR CONTINUITY:
{memories_list}
"""

CHANNEL_TEMPLATE = """\

CHANNEL: #{channel}
"""

TASK_TEMPLATE = """\

TASK:
{task}
"""


def build_spawn_context(identity: str, task: str | None = None, channel: str | None = None) -> str:
    """Assemble spawn context: bootloader for agent execution.

    Provides: identity → space-os context → available primitives → continuity (memories) → task/channel

    Args:
        identity: Agent identity
        task: Task instruction (optional)
        channel: Channel name if responding in channel (optional)

    Returns:
        Complete prompt for agent execution
    """
    agent = agents.get_agent(identity)
    agent_id = agent.agent_id if agent else None

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

    return SPAWN_CONTEXT_TEMPLATE.format(
        identity=identity,
        memories=memories_context,
        task=task_context,
        channel=channel_context,
    )
