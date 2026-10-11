from pydantic import BaseModel, Field
from src.modules.identity.presentation.user.http.response.update_current_user_profile_email import (
    UpdateCurrentUserProfileEmailResponseSchema,
)
from uuid import UUID


class UpdateCurrentUserProfileResponseSchema(BaseModel):
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
    emails: list[UpdateCurrentUserProfileEmailResponseSchema] = Field(
        default_factory=list
    )
