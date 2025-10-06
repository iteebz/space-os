from space.os.core.app import App as BaseApp
from .repo import KnowledgeRepo # Import KnowledgeRepo

class KnowledgeApp(BaseApp):
    def __init__(self):
        super().__init__("knowledge")
        self.register_repository("knowledge", KnowledgeRepo) # Register the repository

    def cli_group(self):
        from .cli import knowledge_group # Defer import
        return knowledge_group

# Instantiate the app
knowledge_app = KnowledgeApp()