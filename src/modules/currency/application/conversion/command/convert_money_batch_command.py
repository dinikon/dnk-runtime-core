from dataclasses import dataclass
from src.modules.currency.application.conversion.dto.conversion_request import (
    ConversionRequest,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


@dataclass(frozen=True, slots=True)
class ConvertMoneyBatchCommand:
    """Immutable input for convert money batch."""

    tenant_id: EntityIdVO
    requests: tuple[ConversionRequest, ...]
    operation_id: EntityIdVO | None = None


__all__ = ["ConvertMoneyBatchCommand"]
