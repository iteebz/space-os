"""Invocation context: unified telemetry and argument handling across CLI."""

from dataclasses import dataclass, field

from space.os import events, spawn


@dataclass
class Invocation:
    """Tracks invocation metadata for telemetry, identity, and aliases."""

    command: str
    identity: str | None = None
    full_args: list[str] = field(default_factory=list)
    subcommand: str | None = None
    _agent_id: str | None = field(default=None, init=False)

    @classmethod
    def from_args(cls, argv: list[str]) -> "Invocation":
        """Parse argv into invocation context (no DB calls)."""
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

        return cls(
            command=command,
            identity=identity,
            full_args=argv,
            subcommand=subcommand,
        )

    @property
    def agent_id(self) -> str | None:
        """Lazily resolve agent_id from identity (cached)."""
        if self._agent_id is None and self.identity:
            self._agent_id = spawn.db.get_agent_id(self.identity)
        return self._agent_id

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
