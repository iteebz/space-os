from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Identity:
    id: str
    type: str
    current_constitution_id: Optional[str]
    created_at: datetime
    updated_at: datetime

@dataclass
class Constitution:
    id: str
    name: str
    version: str
    content: str
    identity_id: Optional[str]
    previous_version_id: Optional[str]
    created_at: datetime
    created_by: str
    change_description: Optional[str]
    hash: str