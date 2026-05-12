from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from src.modules.communication.domain.delivery import (
    DeliveryEvent,
)
from src.modules.communication.domain.outbound_message import (
    OutboundMessage,
)
from src.modules.communication.domain.provider_connector import (
    ProviderConnector,
)


class ProviderWebhookRepositoryProtocol(Protocol):
    async def get_active_connector_by_code(
        self,
        tenant_id: UUID,
        provider_code: str,
    ) -> ProviderConnector | None: ...

    async def find_outbound_by_external_message_id(
        self,
        *,
        tenant_id: UUID,
        external_message_id: str,
    ) -> OutboundMessage | None: ...

    async def add_delivery_event(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID | None,
        provider_connection_id: UUID | None,
        external_message_id: str | None,
        external_status: str | None,
        internal_status: str,
        event_type: str,
        event_at: datetime | None,
        raw_payload: dict[str, Any],
    ) -> DeliveryEvent: ...

    async def update_outbound_status_from_event(
        self,
        *,
        tenant_id: UUID,
        outbound_message_id: UUID,
        external_status: str | None,
        internal_status: str,
        now: datetime,
    ) -> None: ...


__all__ = ["ProviderWebhookRepositoryProtocol"]
