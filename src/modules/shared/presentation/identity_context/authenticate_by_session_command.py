from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticateBySessionCommand:
    """Команда shared authentication process по session cookie."""

    host: str | None
    session_token: str | None
    ip: str | None
    user_agent: str | None


__all__ = ["AuthenticateBySessionCommand"]
