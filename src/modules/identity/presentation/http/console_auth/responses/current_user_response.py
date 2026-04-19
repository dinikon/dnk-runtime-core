from uuid import UUID

from pydantic import BaseModel, Field

from src.modules.identity.presentation.http.console_auth.responses.current_user_email_response import (
    CurrentUserEmailResponseSchema,
)


class CurrentUserResponseSchema(BaseModel):
    """Pydantic-схема профиля текущего пользователя."""

    id: UUID
    status: str
    last_name: str
    first_name: str
    middle_name: str | None
    avatar: str | None
    interface_language: str
    interface_theme: str
    timezone: str
    emails: list[CurrentUserEmailResponseSchema] = Field(default_factory=list)


__all__ = ["CurrentUserResponseSchema"]
