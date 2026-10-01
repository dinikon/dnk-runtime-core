from pydantic import BaseModel, Field
from src.modules.identity.presentation.user.http.response.current_user_email import (
    CurrentUserEmailResponseSchema,
)
from uuid import UUID


class CurrentUserResponseSchema(BaseModel):
    """Pydantic-схема профиля текущего пользователя."""

    id: UUID
    role: str = "member"
    status: str
    last_name: str
    first_name: str
    middle_name: str | None
    avatar: str | None
    interface_language: str
    interface_theme: str
    timezone: str
    emails: list[CurrentUserEmailResponseSchema] = Field(default_factory=list)
