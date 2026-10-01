from __future__ import annotations

from typing import Protocol

from src.modules.identity.domain.auth.principal import Principal
from src.modules.identity.presentation.auth.authenticate_by_session_command import (
    AuthenticateBySessionCommand,
)


class AuthenticationProcessProtocol(Protocol):
    """Порт аутентификации request по session данным."""

    async def authenticate(
        self,
        command: AuthenticateBySessionCommand,
    ) -> Principal | None:
        """Возвращает principal или None для неаутентифицированного request."""
        ...


__all__ = ["AuthenticationProcessProtocol"]
