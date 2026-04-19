from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreatedTenantAdmin:
    """Результат создания tenant admin пользователя."""

    user_id: UUID
    user_email_id: UUID
    user_status: str


__all__ = ["CreatedTenantAdmin"]
