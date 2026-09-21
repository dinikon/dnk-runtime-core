from __future__ import annotations
from datetime import date
from typing import Protocol
from typing import Sequence
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.exchange_rate.value_object.rate_record import (
    RateRecord,
)
from src.modules.currency.domain.policy.value_object.rate_date_policy import (
    RateDatePolicy,
)
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class RateRepository(Protocol):
    """Explicit persistence contract for rate."""

    async def find(
        self,
        *,
        tenant_id: EntityIdVO,
        provider: ProviderCode,
        pair: CurrencyPair,
        requested_date: date,
        policy: RateDatePolicy,
    ) -> RateRecord | None: ...
    async def find_cross(
        self,
        *,
        tenant_id: EntityIdVO,
        provider: ProviderCode,
        pair: CurrencyPair,
        bridge: CurrencyCodeVO,
        requested_date: date,
        policy: RateDatePolicy,
    ) -> tuple[RateRecord, RateRecord] | None: ...
    async def history(
        self,
        *,
        tenant_id: EntityIdVO,
        provider: ProviderCode,
        pair: CurrencyPair | None,
        limit: int,
        offset: int,
    ) -> Sequence[RateRecord]: ...


__all__ = ["RateRepository"]
