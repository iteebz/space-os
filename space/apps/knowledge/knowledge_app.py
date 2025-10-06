from space.os.app import App
from .cli import knowledge_group
from .db import ensure_schema

class KnowledgeApp(App):
    def __init__(self):
        super().__init__("knowledge")

    def cli_group(self):
        return knowledge_group

    def initialize(self):
        ensure_schema(self.db_path)

# Instantiate the app
knowledge_app = KnowledgeApp()
