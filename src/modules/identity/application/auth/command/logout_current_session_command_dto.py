from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogoutCurrentSessionCommandDTO:
    """DTO команды logout текущей session."""

    host: str
    session_token: str | None


__all__ = ["LogoutCurrentSessionCommandDTO"]
