from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthenticateBySessionQuery:
    """Команда аутентификации по session token и request host."""

    host: str | None
    session_token: str | None
