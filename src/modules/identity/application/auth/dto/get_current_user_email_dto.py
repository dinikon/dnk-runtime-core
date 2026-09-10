from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetCurrentUserEmailDTO:
    """DTO email-адреса текущего пользователя."""

    id: UUID
    email: str
    is_primary: bool
    is_verified: bool


__all__ = ["GetCurrentUserEmailDTO"]
