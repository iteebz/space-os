"""Knowledge primitive - agent-contributed learned patterns."""

from .db import list_all, query_by_contributor, query_by_domain, write_knowledge

__all__ = [
    "write_knowledge",
    "query_by_domain",
    "query_by_contributor",
    "list_all",
]
