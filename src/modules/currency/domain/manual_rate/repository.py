from datetime import date, datetime
from decimal import Decimal
from typing import Protocol
from src.modules.currency.domain.exchange_rate.repository import RateRepository
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.manual_rate.entity import ManualExchangeRate
from src.modules.currency.domain.manual_rate.value_object.id import (
    ManualExchangeRateIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class ManualRateRepository(RateRepository, Protocol):
    """Explicit persistence contract for manual rate."""

    async def set_manual(
        self,
        *,
        identifier: ManualExchangeRateIdVO,
        tenant_id: EntityIdVO,
        pair: CurrencyPair,
        rate: Decimal,
        effective_date: date,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> tuple[ManualExchangeRate, bool]: ...


__all__ = ["ManualRateRepository"]
