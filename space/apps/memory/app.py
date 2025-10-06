from space.os.core.app import App
from .cli import memory_group
from .db import ensure_schema
from .repository import MemoryRepository # Import MemoryRepository

class Memory(App):
    def __init__(self):
        super().__init__("memory")
        self.register_repository("memory", MemoryRepository) # Register the repository

    def cli_group(self):
        return memory_group

    def initialize(self):
        self.ensure_db(lambda conn: ensure_schema(conn, Path(__file__).parent))

# Instantiate the app
memory_app = Memory()