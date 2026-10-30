from dataclasses import dataclass

from src.modules.shared.domain.events.integration_event import IntegrationEvent


@dataclass(frozen=True, slots=True)
class ConsumeCatalogStockChangedCommand:
    """Публичное событие владельца Catalog."""

    event: IntegrationEvent
