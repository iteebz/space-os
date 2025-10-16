"""Invocation context: unified telemetry and argument handling across CLI."""

from dataclasses import dataclass, field

from space import events
from space.spawn import registry

IDENTITY_POSITIONAL_COMMANDS = {
    "wake",
    "sleep",
}


@dataclass
class InvocationContext:
    """Tracks invocation metadata for telemetry, identity, and aliases."""

    command: str
    identity: str | None = None
    full_args: list[str] = field(default_factory=list)
    subcommand: str | None = None
    agent_id: str | None = None

    @classmethod
    def from_args(cls, argv: list[str]) -> "InvocationContext":
        """Parse argv into invocation context."""
        if not argv:
            return cls(command="", full_args=argv)

        command = argv[0]
        identity = None
        subcommand = None

        # Extract --as <identity>
        for i, arg in enumerate(argv):
            if arg == "--as" and i + 1 < len(argv):
                identity = argv[i + 1]
                break

        # Extract subcommand (second positional arg if not a flag)
        for arg in argv[1:]:
            if not arg.startswith("-"):
                subcommand = arg
                break

        ctx = cls(
            command=command,
            identity=identity,
            full_args=argv,
            subcommand=subcommand,
        )

        if identity:
            ctx.agent_id = registry.get_agent_id(identity)

        return ctx

    def emit_invocation(self, cmd_str: str | None = None) -> None:
        """Emit invocation event to telemetry."""
        resolved_cmd = cmd_str or self.command
        if self.subcommand:
            resolved_cmd = f"{resolved_cmd} {self.subcommand}"

        events.emit(
            "cli",
            "invocation",
            agent_id=self.agent_id,
            data=resolved_cmd,
        )

    def emit_error(self, error_msg: str, source: str = "cli") -> None:
        """Emit error event with invocation context."""
        events.emit(
            source,
            "error",
            agent_id=self.agent_id,
            data=error_msg,
        )


class AliasResolver:
    """Resolves command aliases and normalizes arguments for unified routing."""

    @staticmethod
    def normalize_args(argv: list[str]) -> list[str]:
        """Normalize argv: rewrite 'wake hailot' to 'wake --as hailot'."""
        if len(argv) < 2:
            return argv

        command = argv[0]
        if command not in IDENTITY_POSITIONAL_COMMANDS:
            return argv

        if "--as" in argv:
            return argv

        next_arg = argv[1]
        if next_arg.startswith("-"):
            return argv

        return [command, "--as", next_arg] + argv[2:]

    @staticmethod
    def get_routes(cmd: str) -> list[str]:
        """Get all valid routes for a command."""
        routes = [cmd]
        if cmd == "bridge":
            routes.append("bridge")
        return routes

    @staticmethod
    def resolve(argv: list[str]) -> InvocationContext:
        """Resolve and normalize argv into invocation context."""
        normalized = AliasResolver.normalize_args(argv)
        return InvocationContext.from_args(normalized)
