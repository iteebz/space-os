from dataclasses import dataclass
from datetime import datetime


@dataclass
class Memory:
    uuid: str
    identity: str
    topic: str
    message: str
    created_at: int

    @property
    def timestamp(self) -> str:
        return datetime.fromtimestamp(self.created_at).strftime("%Y-%m-%d %H:%M")
