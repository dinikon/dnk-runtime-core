from dataclasses import dataclass

from src.modules.communication.domain.provider_connection import (
    ProviderConnectionIdVO,
)
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class UpdateProviderConnectionStatusCommand:
    """Command смены статуса provider connection."""

    tenant_id: EntityIdVO
    provider_connection_id: ProviderConnectionIdVO
    status: str


__all__ = ["UpdateProviderConnectionStatusCommand"]
