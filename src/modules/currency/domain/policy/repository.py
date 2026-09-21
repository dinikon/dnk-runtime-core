from __future__ import annotations
from datetime import datetime
from typing import Protocol
from src.modules.currency.domain.policy.entity import CurrencyPolicy
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CurrencyPolicyRepository(Protocol):
    """Explicit persistence contract for currency policy."""

    async def get(self, *, tenant_id: EntityIdVO) -> CurrencyPolicy: ...
    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        policy: CurrencyPolicy,
        expected_version: int,
        now: datetime,
    ) -> None: ...
    async def lock(self, *, tenant_id: EntityIdVO) -> None: ...


__all__ = ["CurrencyPolicyRepository"]
