from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from src.modules.communication.domain.provider_connection import ProviderConnection
from src.modules.communication.domain.provider_connector import ProviderConnector


class ProviderConnectionRepositoryProtocol(Protocol):
    async def get_connector(
        self,
        tenant_id: UUID,
        provider_connector_id: UUID,
    ) -> ProviderConnector | None: ...

    async def create_connection(
        self,
        *,
        tenant_id: UUID,
        provider_connector_id: UUID,
        connection_code: str,
        connection_name: str,
        channel_code: str,
        config: dict[str, Any],
        secret_ref: str | None,
        secrets_b64: str | None,
        status: str = ...,
    ) -> ProviderConnection: ...

    async def list_connections(self, tenant_id: UUID) -> list[ProviderConnection]: ...


__all__ = ["ProviderConnectionRepositoryProtocol"]
