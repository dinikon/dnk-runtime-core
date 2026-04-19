from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GeneratedSession:
    """Сгенерированные token/session_id и сроки session."""

    token: str
    session_id: str
    issued_at: datetime
    expires_at: datetime


class SessionServiceProtocol(Protocol):
    """Порт генерации пользовательских sessions."""

    def generate(self, *, ttl_seconds: int) -> GeneratedSession:
        """Генерирует session с указанным TTL."""
        ...


class SessionService:
    """Сервис генерации session token и session_id."""

    @classmethod
    def generate(cls, ttl_seconds: int) -> GeneratedSession:
        """Генерирует session token, id, issued_at и expires_at."""
        issued_at = datetime.now(UTC)
        return GeneratedSession(
            token=f"sess_{secrets.token_urlsafe(32)}",
            session_id=secrets.token_urlsafe(12),
            issued_at=issued_at,
            expires_at=issued_at + timedelta(seconds=ttl_seconds),
        )


__all__ = ["GeneratedSession", "SessionService", "SessionServiceProtocol"]
