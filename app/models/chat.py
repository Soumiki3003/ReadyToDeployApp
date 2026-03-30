from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app import utils


class ChatMessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class ChatMessage(BaseModel):
    id: str = Field(default_factory=utils.uuid4_hex)
    role: ChatMessageRole
    content: str
    timestamp: datetime = Field(default_factory=utils.utc_now)
