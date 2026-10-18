from __future__ import annotations
from dataclasses import dataclass, field
from uuid import UUID
from src.modules.identity.application.user.query.get_current_user.email_dto import (
    GetCurrentUserEmailDTO,
)


@dataclass(frozen=True, slots=True)
class GetCurrentUserRecordDTO:
    """Проекция сохранённого профиля без вычисленной эффективной валюты."""

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
    emails: list[GetCurrentUserEmailDTO] = field(default_factory=list)
    role: str = "member"
