from dataclasses import dataclass
from typing import Optional

@dataclass
class Message:
    id: int
    channel_id: str
    sender: str
    content: str
    created_at: str

@dataclass
class Channel:
    name: str

@dataclass
class Note:
    id: int
    channel_id: str
    author: str
    content: str
    created_at: str

@dataclass
class ExportData:
    channel_id: str
    channel_name: str
    messages: list[Message]
    notes: list[Note]
