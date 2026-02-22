from datetime import datetime

from pydantic import BaseModel, Field

from app import utils


class CreateCourse(BaseModel):
    name: str = Field(min_length=2, description="Course name")
    description: str | None = Field(default=None, description="Course description")


class ChatUserMessageFormRequest(BaseModel):
    content: str = Field(description="Content of the message")
    created_at: datetime = Field(
        default_factory=utils.utc_now,
        description="Timestamp of when the message was created",
    )
