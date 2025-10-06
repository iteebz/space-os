from typing import Optional

import click

from space import events
from space.core import guide


class ContextGuideManager:
    def __init__(self, guide_name: str = "memory"):
        self.guide_name = guide_name
        self.guide_content = guide.load_guide_content(self.guide_name)

    def exists(self) -> bool:
        return self.guide_content is not None

    def track_and_echo(self):
        if self.guide_content:
            events.track(self.guide_name, self.guide_content)
            click.echo(self.guide_content)
        else:
            click.echo(f"{self.guide_name}.md not found")

    def get_content(self) -> Optional[str]:
        return self.guide_content

# Instantiate the manager for the 'memory' guide, as used in context/cli.py
memory_guide_manager = ContextGuideManager(guide_name="memory")
