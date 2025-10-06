from space.os.app import BaseApp
from .cli import knowledge_group

class KnowledgeApp(BaseApp):
    def __init__(self):
        super().__init__("knowledge")

    def cli_group(self):
        return knowledge_group

# Instantiate the app
app = KnowledgeApp()

# Make the public API from api.py available on the package level
from .api import (
    write_knowledge,
    query_knowledge,
)

__all__ = [
    "write_knowledge",
    "query_knowledge",
    "app",
]