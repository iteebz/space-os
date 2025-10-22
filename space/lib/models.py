from dataclasses import dataclass


@dataclass
class Message:
    role: str
    text: str
    timestamp: str
    session_id: str
    model: str | None = None

    def is_valid(self) -> bool:
        return bool(self.role and self.text and self.timestamp and self.session_id)
