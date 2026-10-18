from __future__ import annotations
from dataclasses import dataclass, field
from uuid import UUID
from src.modules.identity.application.user.command.update_current_user_profile.email_dto import (
    UpdateCurrentUserProfileEmailDTO,
)


@dataclass(frozen=True, slots=True)
class UpdateCurrentUserProfileResultDTO:
    """DTO результата обновления профиля текущего пользователя."""

    id: UUID
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
    emails: list[UpdateCurrentUserProfileEmailDTO] = field(default_factory=list)
    role: str = "member"
