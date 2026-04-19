from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LogoutCurrentSessionResultDTO:
    """DTO результата logout текущей session."""

    ok: bool


__all__ = ["LogoutCurrentSessionResultDTO"]
