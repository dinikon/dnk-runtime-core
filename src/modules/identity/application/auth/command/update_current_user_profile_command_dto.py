from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UpdateCurrentUserProfileCommandDTO:
    """DTO команды обновления профиля текущего пользователя."""

    host: str
    session_token: str | None
    last_name: str
    first_name: str
    middle_name: str | None
    interface_language: str
    interface_theme: str | None
    timezone: str


__all__ = ["UpdateCurrentUserProfileCommandDTO"]
