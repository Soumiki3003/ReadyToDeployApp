from pydantic import BaseModel, EmailStr, SecretStr, Field

from app.models.user import UserRole


class CreateUser(BaseModel):
    name: str = Field(min_length=2)
    email: EmailStr
    password: SecretStr = Field(min_length=8)
    role: UserRole = Field(default=UserRole.STUDENT)
    enabled: bool = Field(default=True)


class UpdateUser(BaseModel):
    name: str | None = Field(default=None, min_length=2)
    email: EmailStr | None = None
    password: SecretStr | None = Field(default=None, min_length=8)
    role: UserRole | None = None
    enabled: bool | None = None
