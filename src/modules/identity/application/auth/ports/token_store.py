from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OtpChallenge:
    token: str
    email: str
    tenant_id: UUID
    tenant_domain_id: UUID
    host: str
    code_hash: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class SessionRecord:
    token: str
    session_id: str
    user_id: UUID
    tenant_id: UUID
    tenant_domain_id: UUID
    host: str
    issued_at: datetime
    expires_at: datetime


class OtpChallengeStorePort(Protocol):
    async def create_challenge(
        self, challenge: OtpChallenge, ttl_seconds: int
    ) -> None: ...
    async def get_challenge(
        self, tenant_id: UUID, token: str
    ) -> OtpChallenge | None: ...
    async def invalidate_challenge(self, tenant_id: UUID, token: str) -> None: ...


class SessionStorePort(Protocol):
    async def create_session(
        self, session: SessionRecord, ttl_seconds: int
    ) -> None: ...
    async def get_session(
        self, tenant_id: UUID, token: str
    ) -> SessionRecord | None: ...
    async def invalidate_session(self, tenant_id: UUID, token: str) -> None: ...
