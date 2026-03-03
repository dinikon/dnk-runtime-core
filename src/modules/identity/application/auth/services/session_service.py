from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GeneratedSession:
    token: str
    session_id: str
    issued_at: datetime
    expires_at: datetime


class SessionServiceProtocol(Protocol):
    def generate(self, *, ttl_seconds: int) -> GeneratedSession: ...


class SessionService:
    def generate(self, *, ttl_seconds: int) -> GeneratedSession:
        issued_at = datetime.now(UTC)
        return GeneratedSession(
            token=f"sess_{secrets.token_urlsafe(32)}",
            session_id=secrets.token_urlsafe(12),
            issued_at=issued_at,
            expires_at=issued_at + timedelta(seconds=ttl_seconds),
        )
