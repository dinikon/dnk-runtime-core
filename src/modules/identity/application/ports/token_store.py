from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OtpChallenge:
    """Сериализуемая запись OTP challenge для email login."""

    token: str
    email: str
    tenant_id: UUID
    tenant_domain_id: UUID
    host: str
    code_hash: str
    created_at: datetime


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


class OtpChallengeStorePort(Protocol):
    """Порт хранения OTP challenges."""

    async def create_challenge(self, challenge: OtpChallenge, ttl_seconds: int) -> None:
        """Сохраняет OTP challenge с TTL."""
        ...

    async def get_challenge(self, tenant_id: UUID, token: str) -> OtpChallenge | None:
        """Возвращает OTP challenge tenant по token или None."""
        ...

    async def invalidate_challenge(self, tenant_id: UUID, token: str) -> None:
        """Удаляет OTP challenge tenant по token."""
        ...


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


__all__ = [
    "OtpChallenge",
    "OtpChallengeStorePort",
    "SessionRecord",
    "SessionStorePort",
]
