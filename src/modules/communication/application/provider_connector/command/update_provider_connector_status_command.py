from dataclasses import dataclass

from src.modules.communication.domain.provider_connector import ProviderConnectorIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class UpdateProviderConnectorStatusCommand:
    """Command смены статуса provider connector."""

    tenant_id: EntityIdVO
    provider_connector_id: ProviderConnectorIdVO
    status: str


__all__ = ["UpdateProviderConnectorStatusCommand"]
