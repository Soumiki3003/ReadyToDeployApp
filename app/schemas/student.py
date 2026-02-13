from pydantic import BaseModel, EmailStr, Field


class CreateStudent(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    password: str = Field(min_length=8)
    enabled: bool = Field(default=True)


class UpdateStudent(BaseModel):
    name: str | None = Field(default=None, min_length=2)
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8)
    enabled: bool | None = None
