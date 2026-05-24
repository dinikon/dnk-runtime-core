from __future__ import annotations

from typing import Protocol

from src.modules.shared.domain.identity_context import Principal
from src.modules.shared.presentation.identity_context.authenticate_by_session_command import (
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
