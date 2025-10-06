from space.os.core.app import App
from .cli import spawn_group
# from .repository import SpawnRepo # Assuming a repo will exist

class Spawn(App):
    def __init__(self):
        super().__init__("spawn")
        # self.register_repository("spawn", SpawnRepo) # Register the repository if a repo exists

    def cli_group(self):
        return spawn_group

# Instantiate the app
spawn_app = Spawn()