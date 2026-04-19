from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.modules.identity.application.auth.command import AuthenticateBySessionCommand
from src.modules.identity.application.ports import (
    SessionStorePort,
    TenantContextReaderPort,
)
from src.modules.identity.domain.user import UserRepositoryProtocol
from src.modules.shared.http.host import normalize_host
from src.modules.tenancy.domain.tenant_domain import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)


@dataclass(frozen=True, slots=True)
class SessionPrincipal:
    """Principal, восстановленный из валидной session."""

    user_id: str
    tenant_id: str | None
    session_id: str
    roles: tuple[str, ...]
    permissions: tuple[str, ...] = ()
    is_authenticated: bool = True


class AuthenticateBySessionUseCaseProtocol(Protocol):
    """Порт use case аутентификации по session."""

    async def execute(
        self,
        dto: AuthenticateBySessionCommand,
    ) -> SessionPrincipal | None:
        """Возвращает principal или None, если session не валидна."""
        ...


class AuthenticateBySessionUseCase(AuthenticateBySessionUseCaseProtocol):
    """Use case восстановления principal из session token."""

    def __init__(
        self,
        tenant_context_reader: TenantContextReaderPort,
        users_repository: UserRepositoryProtocol,
        session_store: SessionStorePort,
    ):
        """Инициализирует use case reader-ом tenant context, user repo и session store."""
        self._tenant_context_reader = tenant_context_reader
        self._users_repository = users_repository
        self._session_store = session_store

    async def execute(
        self,
        dto: AuthenticateBySessionCommand,
    ) -> SessionPrincipal | None:
        """Проверяет session token и возвращает SessionPrincipal для active user."""
        host = normalize_host(dto.host or "")
        session_token = dto.session_token

        if not host or not session_token:
            return None

        try:
            tenant_context = await self._tenant_context_reader.get_by_host(host)
        except (TenantHostNotFoundError, TenantLoginUnavailableError):
            return None

        session = await self._session_store.get_session(
            tenant_context.tenant_id,
            session_token,
        )
        if session is None:
            return None
        if (
            session.tenant_id != tenant_context.tenant_id
            or session.tenant_domain_id != tenant_context.tenant_domain_id
            or session.host != tenant_context.host
        ):
            return None

        user = await self._users_repository.get_by_id(session.user_id)
        if user is None or user.tenant_id != tenant_context.tenant_id:
            return None
        if not user.can_login():
            return None

        return SessionPrincipal(
            user_id=str(user.id),
            tenant_id=str(tenant_context.tenant_id),
            session_id=session.session_id,
            roles=(),
            permissions=(),
            is_authenticated=True,
        )


__all__ = [
    "AuthenticateBySessionUseCase",
    "AuthenticateBySessionUseCaseProtocol",
    "SessionPrincipal",
]
