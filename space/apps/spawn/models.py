from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Identity:
    id: str
    type: str
    created_at: int
    updated_at: int

    @property
    def created_at_iso(self) -> str:
        return datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat()

    @property
    def updated_at_iso(self) -> str:
        return datetime.fromtimestamp(self.updated_at, tz=timezone.utc).isoformat()
