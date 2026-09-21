from datetime import datetime
from typing import Protocol
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ActivationScheduler(Protocol):
    """Schedule a tenant period activation in the caller’s transaction."""

    async def schedule(
        self,
        *,
        tenant_id: EntityIdVO,
        period_id: EntityIdVO,
        run_at: datetime,
        policy_version: int,
        now: datetime,
    ) -> None: ...


__all__ = ["ActivationScheduler"]
