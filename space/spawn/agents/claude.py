from space.lib import agents as lib_agents


class Claude:
    """Claude agent via CLI."""

    def __init__(self, identity: str):
        self.identity = identity

    def run(self, prompt: str | None = None) -> str:
        """Run agent. None = interactive, str = one-shot task."""
        return lib_agents.claude.spawn(self.identity, prompt)
