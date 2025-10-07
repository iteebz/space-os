from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

@dataclass
class Identity:
    id: str
    type: str
    created_at: int
    updated_at: int
    current_constitution_id: Optional[str] = None

    @property
    def created_at_iso(self) -> str:
        return datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat()

    @property
    def updated_at_iso(self) -> str:
        return datetime.fromtimestamp(self.updated_at, tz=timezone.utc).isoformat()

@dataclass
class Constitution:
    id: str
    identity_id: str
    name: str
    version: str
    content: str
    created_by: str
    change_description: str
    created_at: int
    previous_version_id: Optional[str] = None

    @property
    def created_at_iso(self) -> str:
        return datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat()