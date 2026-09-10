from __future__ import annotations

from src.modules.identity.application.auth import (
    AuthenticateBySessionCommand as AuthenticateBySessionUseCaseCommand,
    SessionPrincipal,
)
from src.modules.identity.presentation.depends import AuthenticateBySessionUseCaseDep
from src.modules.shared.domain.identity_context import Principal
from src.modules.shared.presentation.identity_context.authenticate_by_session_command import (
    AuthenticateBySessionCommand,
)
from src.modules.shared.presentation.identity_context.authentication_process_protocol import (
    AuthenticationProcessProtocol,
)


class AuthenticateBySessionUseCaseAdapter(AuthenticationProcessProtocol):
    """Адаптер shared auth-порта к identity AuthenticateBySessionUseCase."""

    def __init__(self, use_case: AuthenticateBySessionUseCaseDep) -> None:
        """Сохраняет identity use case для последующей аутентификации."""
        self._use_case = use_case

    async def authenticate(
        self,
        command: AuthenticateBySessionCommand,
    ) -> Principal | None:
        """Аутентифицирует session и мапит identity principal в shared Principal."""
        principal = await self._use_case(
            AuthenticateBySessionUseCaseCommand(
                host=command.host,
                session_token=command.session_token,
                ip=command.ip,
                user_agent=command.user_agent,
            )
        )
        if principal is None:
            return None
        return _map_principal(principal)


def _map_principal(principal: SessionPrincipal) -> Principal:
    """Мапит identity SessionPrincipal в shared Principal."""
    return Principal(
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        session_id=principal.session_id,
        roles=principal.roles,
        permissions=principal.permissions,
        is_authenticated=principal.is_authenticated,
    )


__all__ = ["AuthenticateBySessionUseCaseAdapter"]
