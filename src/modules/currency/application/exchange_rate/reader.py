from datetime import date
from typing import Sequence
from src.modules.currency.domain.exchange_rate.repository import RateRepository
from src.modules.currency.domain.manual_rate.repository import ManualRateRepository
from src.modules.currency.domain.provider.value_object.provider_code import ProviderCode
from src.modules.currency.domain.provider_rate.repository import ProviderRateRepository
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.exchange_rate.value_object.rate_record import (
    RateRecord,
)
from src.modules.currency.domain.policy.value_object.rate_date_policy import (
    RateDatePolicy,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class RateReader:
    """Select exactly one local repository according to the chosen source."""

    def __init__(self, manual: ManualRateRepository, provider: ProviderRateRepository):
        self.manual, self.provider = manual, provider

    def _source(self, provider: ProviderCode) -> RateRepository:
        return self.manual if provider == ProviderCode("MANUAL") else self.provider

    async def find(
        self,
        *,
        tenant_id: EntityIdVO,
        provider: ProviderCode,
        pair: CurrencyPair,
        requested_date: date,
        policy: RateDatePolicy,
    ) -> RateRecord | None:
        return await self._source(provider).find(
            tenant_id=tenant_id,
            provider=provider,
            pair=pair,
            requested_date=requested_date,
            policy=policy,
        )

    async def find_cross(
        self,
        *,
        tenant_id: EntityIdVO,
        provider: ProviderCode,
        pair: CurrencyPair,
        bridge: CurrencyCodeVO,
        requested_date: date,
        policy: RateDatePolicy,
    ) -> tuple[RateRecord, RateRecord] | None:
        return await self._source(provider).find_cross(
            tenant_id=tenant_id,
            provider=provider,
            pair=pair,
            bridge=bridge,
            requested_date=requested_date,
            policy=policy,
        )

    async def history(
        self,
        *,
        tenant_id: EntityIdVO,
        provider: ProviderCode,
        pair: CurrencyPair | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence[RateRecord]:
        return await self._source(provider).history(
            tenant_id=tenant_id,
            provider=provider,
            pair=pair,
            limit=limit,
            offset=offset,
        )


__all__ = ["RateReader"]
