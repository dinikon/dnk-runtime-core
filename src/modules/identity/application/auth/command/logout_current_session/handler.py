from __future__ import annotations
from src.modules.identity.application.auth.command.logout_current_session.command import (
    LogoutCurrentSessionCommand,
)
from src.modules.identity.application.auth.command.logout_current_session.dto import (
    LogoutCurrentSessionResultDTO,
)
from src.modules.identity.application.auth.port.session_store import SessionStorePort
from src.modules.identity.application.auth.port.tenant_context_reader import (
    TenantContextReaderPort,
)
from src.modules.shared.application.network.host import normalize_host


class LogoutCurrentSessionHandler:
    """Use case logout текущей session."""

    def __init__(
        self,
        tenant_context_reader: TenantContextReaderPort,
        session_store: SessionStorePort,
    ):
        """Инициализирует use case tenant context reader и session store."""
        self._tenant_context_reader = tenant_context_reader
        self._session_store = session_store

    async def execute(
        self, dto: LogoutCurrentSessionCommand
    ) -> LogoutCurrentSessionResultDTO:
        """Идемпотентно инвалидирует session token, если он валиден для tenant host."""
        host = normalize_host(dto.host)
        tenant_context = await self._tenant_context_reader.get_by_host(host)
        if not dto.session_token:
            return LogoutCurrentSessionResultDTO(ok=True)
        session = await self._session_store.get_session(
            tenant_context.tenant_id, dto.session_token
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
            tenant_context.tenant_id, dto.session_token
        )
        return LogoutCurrentSessionResultDTO(ok=True)
