from dataclasses import dataclass

from src.modules.communication.domain.provider_connector import ProviderConnectorIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class DeleteProviderConnectorCommand:
    """Command удаления provider connector."""

    tenant_id: EntityIdVO
    provider_connector_id: ProviderConnectorIdVO


__all__ = ["DeleteProviderConnectorCommand"]
