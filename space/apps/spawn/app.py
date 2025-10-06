from space.os.core.app import App
from space.apps.spawn.repo import SpawnRepo
from .cli import spawn_group # Import the cli_group

class Spawn(App):
    def __init__(self):
        super().__init__("spawn")
        self.register_repository("spawn", SpawnRepo) # Register the repository
        from . import api
        api._set_spawn_app_instance(self)

    def cli_group(self):
        """
        The click command group for this application.
        """
        return spawn_group

    def initialize(self):
        self.ensure_db()
        # Explicitly call create_table on the registered repository
        self.repositories["spawn"].create_table()

spawn_app = Spawn()