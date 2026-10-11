from __future__ import annotations
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class UpdateCurrentUserProfileEmailDTO:
    """DTO email-адреса результата обновления профиля."""

    id: UUID
    email: str
    is_primary: bool
    is_verified: bool
