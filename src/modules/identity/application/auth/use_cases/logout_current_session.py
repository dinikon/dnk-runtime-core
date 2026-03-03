from __future__ import annotations

from src.modules.identity.application.auth.dto import (
    LogoutCurrentSessionCommandDTO,
    LogoutCurrentSessionResultDTO,
)
from src.modules.identity.application.auth.ports.tenant_context import (
    TenantContextReaderPort,
)
from src.modules.identity.application.auth.ports.token_store import (
    SessionStorePort,
)
from src.modules.identity.domain.errors import (
    TenantHostNotFoundError,
    TenantLoginUnavailableError,
)


class LogoutCurrentSessionUseCase:
    def __init__(
        self,
        tenant_context_reader: TenantContextReaderPort,
        session_store: SessionStorePort,
    ):
        self._tenant_context_reader = tenant_context_reader
        self._session_store = session_store

    async def execute(
        self,
        dto: LogoutCurrentSessionCommandDTO,
    ) -> LogoutCurrentSessionResultDTO:
        host = dto.host.strip().lower()
        tenant_context = await self._tenant_context_reader.get_by_host(host)
        if tenant_context is None:
            raise TenantHostNotFoundError(host)
        if (
            tenant_context.tenant_status != "active"
            or tenant_context.domain_status != "active"
        ):
            raise TenantLoginUnavailableError(host)

        if not dto.session_token:
            return LogoutCurrentSessionResultDTO(ok=True)

        session = await self._session_store.get_session(
            tenant_context.tenant_id,
            dto.session_token,
        )
        if session is None:
            return LogoutCurrentSessionResultDTO(ok=True)
        if (
            session.tenant_id != tenant_context.tenant_id
            or session.tenant_domain_id != tenant_context.tenant_domain_id
            or session.host != tenant_context.host
        ):
            return LogoutCurrentSessionResultDTO(ok=True)

        await self._session_store.invalidate_session(
            tenant_context.tenant_id,
            dto.session_token,
        )
        return LogoutCurrentSessionResultDTO(ok=True)
