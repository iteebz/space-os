"""Message formatting for council output."""

from datetime import datetime

from space.os.spawn import db as spawn_db


class Colors:
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    GRAY = "\033[90m"
    YELLOW = "\033[33m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def _styled(text: str, *colors: str) -> str:
    """Apply colors to text with automatic reset."""
    return f"{''.join(colors)}{text}{Colors.RESET}"


def format_message(msg, is_user: bool) -> str:
    """Format a message for display in council.

    Args:
        msg: Message object with agent_id, created_at, content
        is_user: Whether this is a user/human message

    Returns:
        Formatted message string with colors and styling
    """
    identity = spawn_db.get_identity(msg.agent_id) or msg.agent_id
    ts = datetime.fromisoformat(msg.created_at).strftime("%H:%M:%S")

    if is_user:
        prefix = _styled(">", Colors.CYAN)
        ts_part = _styled(ts, Colors.CYAN)
        id_part = _styled(identity, Colors.BOLD)
        return f"{prefix} {ts_part} {id_part}: {msg.content}"
    ts_part = _styled(ts, Colors.WHITE)
    id_part = _styled(identity, Colors.BOLD)
    return f"{ts_part} {id_part}: {msg.content}"


def format_header(channel_name: str, topic: str | None = None) -> str:
    """Format channel header.

    Args:
        channel_name: Name of the channel
        topic: Optional topic description

    Returns:
        Formatted header string
    """
    title = _styled(f"📡 {channel_name}", Colors.BOLD, Colors.CYAN)
    lines = [f"\n{title}"]
    if topic:
        lines.append(f"   {_styled(topic, Colors.GRAY)}")
    lines.append("")
    return "\n".join(lines)


def format_error(msg: str) -> str:
    """Format error message."""
    warn = _styled("⚠", Colors.YELLOW)
    return f"\n{warn}  {msg}\n"
