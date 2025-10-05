"""Knowledge primitive - agent-contributed learned patterns."""

from .storage import write_knowledge, query_by_domain, query_by_contributor, list_all

__all__ = [
    "write_knowledge",
    "query_by_domain",
    "query_by_contributor",
    "list_all",
]
