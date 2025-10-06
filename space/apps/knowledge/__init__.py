from .app import knowledge_app as app

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