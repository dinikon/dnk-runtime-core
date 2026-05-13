from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from src.modules.communication.domain.provider_connector import (
    ProviderConnector,
    ProviderMessageType,
)


class ProviderConnectorRepositoryProtocol(Protocol):
    async def upsert_connector(
        self,
        *,
        tenant_id: UUID,
        provider_code: str,
        provider_name: str,
        version: str,
        connector_type: str,
        yaml_spec: dict[str, Any],
        yaml_checksum: str,
        status: str = ...,
    ) -> ProviderConnector: ...

    async def upsert_message_type(
        self,
        *,
        tenant_id: UUID,
        provider_connector_id: UUID,
        message_type_code: str,
        channel_code: str,
        name: str,
        field_schema: dict[str, Any],
        ui_schema: dict[str, Any],
        is_active: bool = ...,
    ) -> ProviderMessageType: ...

    async def list_connectors(self, tenant_id: UUID) -> list[ProviderConnector]: ...

    async def list_message_types(
        self,
        tenant_id: UUID,
        provider_connector_id: UUID | None = None,
    ) -> list[ProviderMessageType]: ...


__all__ = ["ProviderConnectorRepositoryProtocol"]
