from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.modules.communication.domain.delivery import DeliveryEventIdVO
from src.modules.communication.domain.provider_connector import ProviderConnectorCodeVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class HandleProviderWebhookCommand:
    """Команда обработки provider webhook."""

    tenant_id: EntityIdVO
    delivery_event_id: DeliveryEventIdVO
    provider_code: ProviderConnectorCodeVO
    raw_payload: dict[str, Any]


__all__ = ["HandleProviderWebhookCommand"]
