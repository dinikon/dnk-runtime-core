from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from .get_current_user_email_dto import GetCurrentUserEmailDTO


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
    interface_theme: str | None
    timezone: str
    emails: list[GetCurrentUserEmailDTO] = field(default_factory=list)


__all__ = ["UpdateCurrentUserProfileResultDTO"]
