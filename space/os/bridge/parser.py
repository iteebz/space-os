import re
import subprocess

from space.os import config, events

AGENT_PROMPT_TEMPLATE = """{context}

[TASK INSTRUCTIONS]
{task}

Infer the actual task from bridge context. If ambiguous, ask for clarification."""


def extract_mention_task(identity: str, content: str) -> str:
    """Extract task following @identity mention. Returns task or empty string."""
    pattern = rf"@{re.escape(identity)}\s+(.*?)(?=@|\Z)"
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ""


def parse_mentions(content: str) -> list[str]:
    """Extract @identity mentions from content. Returns list of identities."""
    pattern = r"@([\w-]+)"
    matches = re.findall(pattern, content)
    return list(set(matches))


def should_spawn(identity: str, content: str) -> bool:
    """Check if identity is a valid spawn identity."""
    config.init_config()
    cfg = config.load_config()
    return identity in cfg.get("roles", {})


def spawn_from_mention(identity: str, channel: str, content: str) -> str | None:
    """Spawn agent from bridge mention with limited context."""
    if not should_spawn(identity, content):
        return None

    try:
        # Export full channel context
        export = subprocess.run(
            ["bridge", "export", channel],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if export.returncode != 0:
            return None

        # Limit context to last 10 messages to avoid token bloat
        context_lines = export.stdout.split("\n")
        msg_start = next((i for i, line in enumerate(context_lines) if line.startswith("[")), 0)
        messages = [line for line in context_lines[msg_start:] if line.startswith("[")]
        if len(messages) > 10:
            limited_context = (
                "\n".join(context_lines[:msg_start]) + "\n" + "\n".join(messages[-10:])
            )
        else:
            limited_context = export.stdout

        task = extract_mention_task(identity, content)
        return AGENT_PROMPT_TEMPLATE.format(context=limited_context, task=task)
    except Exception as e:
        import sys

        print(f"[ERROR] Building prompt for {identity} failed: {e}", file=sys.stderr)
        return None


def process_message(channel: str, content: str) -> list[tuple[str, str]]:
    """
    Process bridge message for @mentions.
    Returns list of (identity, output) tuples for successful spawns.
    """
    mentions = parse_mentions(content)
    results = []

    for identity in mentions:
        output = spawn_from_mention(identity, channel, content)
        if output:
            results.append((identity, output))
            events.emit(
                "bridge",
                "agent_spawned_from_mention",
                identity,
                f"Channel: {channel}, Output: {output[:100]}",
            )

    return results
