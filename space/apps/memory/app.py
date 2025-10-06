from space.apps.memory import api # Import the API module
from space.os.core.app import App
from .cli import memory_group
from .repo import MemoryRepo # Import MemoryRepo

class Memory(App):
    def __init__(self):
        super().__init__("memory")
        self.register_repository("memory", MemoryRepo)
        api._set_memory_repo_instance(self.repositories['memory']) # Inject the repository into the API module

    def cli_group(self):
        return memory_group

    def initialize(self):
        self.ensure_db()

# Instantiate the app
memory_app = Memory()