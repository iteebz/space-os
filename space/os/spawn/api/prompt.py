"""Agent launching: unified context injection and spawn context assembly."""

from space.os import memory

from . import agents

SPAWN_CONTEXT_TEMPLATE = """\
You are {identity}, powered by {model}.

PRIMITIVES (actual API with examples):
- memory add/list/search/core/inspect/archive: Working memory organized by --topic.
  → memory add "resolved X via Y approach" --topic observations
- bridge send/recv: Immutable async coordination on named channels.
  → bridge send general "here's my thinking on X"
  → bridge recv general  (read channel history before deciding)
- knowledge add/search: Shared discoveries persisted and queryable.
- context search: Unified search across memory, knowledge, bridge, chats, canon.
  → context search "precedent for X pattern" --as {identity}

AGENT DISCOVERY:
→ spawn agents  (see all agents, their roles, and what they do)
→ spawn inspect <agent-name>  (see full details)

DECISION TREE:
WHEN STUCK → spawn agents to find the right agent, then bridge send @agent_name
WHEN NEED USER INPUT → bridge send <channel> "[question] @human" then exit (you'll resume when user @mentions you)
WHEN LEARNING → memory add "insight" --topic observations
WHEN SESSION DONE → memory add "session summary" --topic journal

COORDINATION:
You are part of a multi-agent system. Your completion message MUST hand off to next agent or human.

Examples:
  "Implementation complete. @prime please review session X"
  "Analysis done. @human awaiting decision on approach"
  "Feature shipped, CI passing. @human work complete"

Run `spawn agents` to see available agents and their roles.
Default: when uncertain who's next, ask @human.

{memories}{task}{channel}{task_mode}"""

MEMORIES_TEMPLATE = """\
YOUR CONTINUITY:
{memories_list}
"""

CHANNEL_TEMPLATE = """\

CHANNEL: #{channel}
Post progress and results to this channel using: bridge send {channel} "<message>"
"""

TASK_TEMPLATE = """\

TASK:
{task}
"""

TASK_MODE_TEMPLATE = """\

EXECUTION MODE: Task-based spawn (non-interactive).{cwd_instruction}
"""

TASK_MODE_CWD_INSTRUCTION = """
IMPORTANT: Always cd to ~/space/ first before executing commands. Example:
  cd ~/space && your-command-here
Verify with: cd ~/space && pwd"""


def build_spawn_context(
    identity: str,
    task: str | None = None,
    channel: str | None = None,
    is_ephemeral: bool = False,
    is_continue: bool = False,
) -> str:
    """Assemble spawn context: bootloader for agent execution.

    Provides: identity → space-os context → available primitives → continuity (memories) → task/channel → execution mode notice

    Args:
        identity: Agent identity
        task: Task instruction (optional)
        channel: Channel name if responding in channel (optional)
        is_ephemeral: Whether this is an ephemeral spawn (sets execution mode notice)
        is_continue: Whether resuming existing session (omits cwd instruction)

    Returns:
        Complete prompt for agent execution
    """
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

    task_mode_context = ""
    if is_ephemeral:
        cwd_instruction = "" if is_continue else TASK_MODE_CWD_INSTRUCTION
        task_mode_context = TASK_MODE_TEMPLATE.format(cwd_instruction=cwd_instruction)

    return SPAWN_CONTEXT_TEMPLATE.format(
        identity=identity,
        model=model,
        memories=memories_context,
        task=task_context,
        channel=channel_context,
        task_mode=task_mode_context,
    )
