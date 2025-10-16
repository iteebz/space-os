import subprocess

from space import config


class Claude:
    """Claude agent via CLI."""

    def __init__(self, identity: str):
        """Initialize with identity (maps to constitution + model via config)."""
        self.identity = identity
        config.init_config()
        cfg = config.load_config()

        if identity not in cfg["roles"]:
            raise ValueError(f"Unknown identity: {identity}")

        role_cfg = cfg["roles"][identity]
        self.constitution = role_cfg["constitution"]
        self.base_identity = role_cfg["base_identity"]

        agent_cfg = cfg.get("agents", {}).get(self.base_identity)
        if not agent_cfg:
            raise ValueError(f"Agent not configured: {self.base_identity}")

        self.model = agent_cfg.get("model")
        self.command = agent_cfg.get("command")

    def run(self, prompt: str | None = None) -> str:
        """Run agent. None = interactive, str = one-shot task."""
        if prompt is None:
            return self._interactive()
        return self._task(prompt)

    def _interactive(self) -> str:
        """Launch interactive agent session."""
        from space.spawn import spawn

        spawn.launch_agent(
            role=self.identity.split("-")[0] if "-" in self.identity else self.identity,
            identity=self.identity,
            base_identity=self.base_identity,
            model=self.model,
        )
        return ""

    def _task(self, prompt: str) -> str:
        """Execute one-shot task and return output."""
        allowed_tools = "Bash Edit Read Glob Grep LS Write WebFetch"
        result = subprocess.run(
            [self.command, "-p", prompt, "--allowedTools", allowed_tools],
            capture_output=True,
            text=True,
        )
        return result.stdout
