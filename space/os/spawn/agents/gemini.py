from space.os.lib import agents as lib_agents


class Gemini:
    """Gemini agent via CLI."""

    def __init__(self, identity: str):
        self.identity = identity

    def run(self, prompt: str | None = None) -> str:
        """Run agent. None = interactive, str = one-shot task."""
        return lib_agents.gemini.spawn(self.identity, prompt)
