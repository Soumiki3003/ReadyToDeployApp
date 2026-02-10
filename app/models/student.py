from datetime import datetime, timezone
from typing import Any
from pydantic import BaseModel, EmailStr, Field, model_validator


class Student(BaseModel):
    id: Any | None = None
    name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=8)
    enabled: bool = Field(default=True, index=True)


class StudentTrajectory(BaseModel):
    id: Any | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    query: str
    retrieved_nodes: list[str] = Field(default_factory=list)
    scores: list[float] = Field(default_factory=list)
    interaction_type: str
    query_repeat_count: int = Field(0, ge=0)
    node_entry_count: int = Field(0, ge=0)
    response_time_sec: float = Field(0.0, ge=0.0)
    hint_triggered: bool = Field(default=False, index=True)
    hint_reason: str | None = None
    hint_text: str | None = None

    student_id: Any

    @model_validator(mode="after")
    def validate_scores_length(self):
        if len(self.scores) != len(self.retrieved_nodes):
            raise ValueError("Length of scores must match length of retrieved_nodes")
        return self

    @model_validator(mode="after")
    def validate_hint_fields(self):
        if self.hint_triggered:
            if not self.hint_reason:
                raise ValueError(
                    "hint_reason must be provided if hint_triggered is True"
                )
            if not self.hint_text:
                raise ValueError("hint_text must be provided if hint_triggered is True")
        return self
