from pydantic import BaseModel, Field
from src.modules.identity.presentation.user.http.response.get_current_user_email import (
    GetCurrentUserEmailResponseSchema,
)
from uuid import UUID


class GetCurrentUserResponseSchema(BaseModel):
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
    display_currency: str | None
    effective_display_currency: str
    emails: list[GetCurrentUserEmailResponseSchema] = Field(default_factory=list)
