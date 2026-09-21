from __future__ import annotations
from datetime import datetime, date
from typing import Protocol
from typing import Sequence
from src.modules.currency.domain.functional_currency.entity import (
    FunctionalCurrencyPeriod,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class FunctionalCurrencyRepository(Protocol):
    """Explicit persistence contract for functional currency."""

    async def get_for_date(
        self, *, tenant_id: EntityIdVO, business_date: date
    ) -> FunctionalCurrencyPeriod: ...
    async def list_periods(
        self, *, tenant_id: EntityIdVO
    ) -> Sequence[FunctionalCurrencyPeriod]: ...
    async def add(
        self, *, tenant_id: EntityIdVO, period: FunctionalCurrencyPeriod
    ) -> None: ...
    async def close(
        self, *, tenant_id: EntityIdVO, period_id: EntityIdVO, valid_to: date
    ) -> None: ...

    async def get_by_id(
        self, *, tenant_id: EntityIdVO, period_id: EntityIdVO
    ) -> FunctionalCurrencyPeriod: ...
    async def mark_activated(
        self, *, tenant_id: EntityIdVO, period_id: EntityIdVO, now: datetime
    ) -> bool: ...


__all__ = ["FunctionalCurrencyRepository"]
