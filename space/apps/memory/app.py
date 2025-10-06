from space.os.core.app import App
from .cli import memory_group
from .repo import MemoryRepo

class Memory(App):
    def __init__(self):
        super().__init__("memory")
        self.register_repository("memory", MemoryRepo)

    def cli_group(self):
        return memory_group

    def initialize(self):
        self.ensure_db()

# Instantiate the app
memory_app = Memory()