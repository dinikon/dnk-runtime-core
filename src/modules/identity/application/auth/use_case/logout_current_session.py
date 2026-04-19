from __future__ import annotations

from src.modules.identity.application.auth.command import (
    LogoutCurrentSessionCommandDTO,
)
from src.modules.identity.application.auth.dto.logout_current_session_result_dto import (
    LogoutCurrentSessionResultDTO,
)
from src.modules.identity.application.ports import (
    SessionStorePort,
    TenantContextReaderPort,
)
from src.modules.shared.http.host import normalize_host


class LogoutCurrentSessionUseCase:
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
        self,
        dto: LogoutCurrentSessionCommandDTO,
    ) -> LogoutCurrentSessionResultDTO:
        """Идемпотентно инвалидирует session token, если он валиден для tenant host."""
        host = normalize_host(dto.host)
        tenant_context = await self._tenant_context_reader.get_by_host(host)

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


__all__ = ["LogoutCurrentSessionUseCase"]
