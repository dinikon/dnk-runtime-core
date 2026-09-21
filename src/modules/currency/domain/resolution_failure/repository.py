from typing import Protocol
from src.modules.currency.domain.resolution_failure.entity import ResolutionFailure
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ResolutionFailureRepository(Protocol):
    """Explicit persistence contract for resolution failure."""

    async def add_once(
        self, *, tenant_id: EntityIdVO, failure: ResolutionFailure
    ) -> bool: ...


__all__ = ["ResolutionFailureRepository"]
