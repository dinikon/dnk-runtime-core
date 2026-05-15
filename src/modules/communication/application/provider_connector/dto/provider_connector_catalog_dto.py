from dataclasses import dataclass

from src.modules.communication.application.provider_connector.dto.provider_connector_dto import (
    ProviderConnectorDTO,
)
from src.modules.communication.application.provider_connector.dto.provider_message_type_dto import (
    ProviderMessageTypeDTO,
)


@dataclass(frozen=True, slots=True)
class ProviderConnectorCatalogDTO:
    """DTO списка provider connectors и message types."""

    connectors: list[ProviderConnectorDTO]
    message_types: list[ProviderMessageTypeDTO]


__all__ = ["ProviderConnectorCatalogDTO"]
