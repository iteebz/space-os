from dataclasses import dataclass

@dataclass
class Knowledge:
    id: str
    domain: str
    contributor: str
    content: str
    confidence: float | None
    created_at: str