from .app import knowledge_app as app

# Expose API methods directly from the app's API instance
write_knowledge = app.api.write_knowledge
query_knowledge = app.api.query_knowledge
edit_knowledge = app.api.edit_knowledge
delete_knowledge = app.api.delete_knowledge

__all__ = [
    "write_knowledge",
    "query_knowledge",
    "edit_knowledge",
    "delete_knowledge",
    "app",
]