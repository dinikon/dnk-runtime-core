from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GetCurrentUserQuery:
    """DTO команды получения текущего пользователя по session."""

    host: str
    session_token: str | None
