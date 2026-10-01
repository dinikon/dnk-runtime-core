from __future__ import annotations
from src.modules.identity.application.auth.query.authenticate_by_session.dto import (
    SessionPrincipal,
)
from src.modules.identity.application.auth.query.authenticate_by_session.query import (
    AuthenticateBySessionQuery,
)
from src.modules.identity.application.auth.port.session_store import SessionStorePort
from src.modules.identity.application.auth.port.tenant_context_reader import (
    TenantContextReaderPort,
)
from src.modules.identity.domain.user.repository import UserRepositoryProtocol
from src.modules.identity.domain.user.value_object.user_id import UserIdVO
from src.modules.shared import EntityIdVO
from src.modules.shared.application.network.host import normalize_host
from src.modules.identity.application.auth.port.tenant_context_reader import (
    IdentityTenantNotFoundError,
)
from src.modules.identity.application.auth.port.tenant_context_reader import (
    IdentityTenantUnavailableError,
)


class AuthenticateBySessionHandler:
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

    async def execute(self, dto: AuthenticateBySessionQuery) -> SessionPrincipal | None:
        """Проверяет session token и возвращает SessionPrincipal для active user."""
        host = normalize_host(dto.host or "")
        session_token = dto.session_token
        if not host or not session_token:
            return None
        try:
            tenant_context = await self._tenant_context_reader.get_by_host(host)
        except (IdentityTenantNotFoundError, IdentityTenantUnavailableError):
            return None
        tenant_id = EntityIdVO.from_value(tenant_context.tenant_id)
        session = await self._session_store.get_session(
            tenant_context.tenant_id, session_token
        )
        if session is None:
            return None
        if (
            session.tenant_id != tenant_context.tenant_id
            or session.tenant_domain_id != tenant_context.tenant_domain_id
            or session.host != tenant_context.host
        ):
            return None
        user = await self._users_repository.get_by_id(
            UserIdVO.from_value(session.user_id), tenant_id=tenant_id
        )
        if user is None or user.tenant_id != tenant_id:
            return None
        if not user.can_login() or session.session_epoch != user.session_epoch:
            return None
        return SessionPrincipal(
            user_id=str(user.id.uuid),
            tenant_id=str(tenant_context.tenant_id),
            session_id=session.session_id,
            roles=(user.role,),
            permissions=(),
            is_authenticated=True,
        )
