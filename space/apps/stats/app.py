from space.os.core.app import App
from .cli import stats_group

class Stats(App):
    def __init__(self):
        super().__init__("stats")

    def cli_group(self):
        return stats_group

    def initialize(self):
        # No specific database initialization needed for a stats app
        pass

stats_app = Stats()
