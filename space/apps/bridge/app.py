from space.os.core.app import App
from .cli import bridge_group

class Bridge(App):
    def __init__(self):
        super().__init__("bridge")

    def cli_group(self):
        return bridge_group

    def initialize(self):
        # Bridge app might have specific database initialization or migration needs
        # For now, we'll just ensure the database exists.
        self.ensure_db()

bridge_app = Bridge()
