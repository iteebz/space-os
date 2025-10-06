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

    @classmethod
    def from_row(cls, row: tuple) -> "Memory":
        """Creates a Memory object from a database row."""
        return cls(
            uuid=row[0],
            identity=row[1],
            topic=row[2],
            message=row[3],
            created_at=row[4],
        )
