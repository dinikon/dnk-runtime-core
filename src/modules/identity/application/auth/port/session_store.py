from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SessionRecord:
    """Сериализуемая запись пользовательской session."""

    token: str
    session_id: str
    user_id: UUID
    tenant_id: UUID
    tenant_domain_id: UUID
    host: str
    issued_at: datetime
    expires_at: datetime
    session_epoch: int = 0


class SessionStorePort(Protocol):
    """Порт хранения пользовательских sessions."""

    async def create_session(self, session: SessionRecord, ttl_seconds: int) -> None:
        """Сохраняет session с TTL."""
        ...

    async def get_session(self, tenant_id: UUID, token: str) -> SessionRecord | None:
        """Возвращает session tenant по token или None."""
        ...

    async def invalidate_session(self, tenant_id: UUID, token: str) -> None:
        """Удаляет session tenant по token."""
        ...
