from datetime import date, datetime
from decimal import Decimal
from typing import Protocol, Sequence

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from .models import (
    CurrencyInfo,
    CurrencyPolicy,
    CurrencyPair,
    ProviderCode,
    RateDatePolicy,
    RateRecord,
    FunctionalCurrencyPeriod,
)


class CurrencyDirectory(Protocol):
    async def get(self, code: CurrencyCodeVO) -> CurrencyInfo: ...
    async def exists(self, code: CurrencyCodeVO) -> bool: ...
    async def list_active(self) -> Sequence[CurrencyInfo]: ...


class CurrencyPolicyRepository(Protocol):
    async def get(self, *, tenant_id: EntityIdVO) -> CurrencyPolicy: ...
    async def save(
        self,
        *,
        tenant_id: EntityIdVO,
        policy: CurrencyPolicy,
        expected_version: int,
        now: datetime,
    ) -> None: ...
    async def enabled(self, *, tenant_id: EntityIdVO) -> set[CurrencyCodeVO]: ...
    async def set_enabled(
        self,
        *,
        tenant_id: EntityIdVO,
        code: CurrencyCodeVO,
        enabled: bool,
        now: datetime,
    ) -> None: ...
    async def lock(self, *, tenant_id: EntityIdVO) -> None: ...


class FunctionalCurrencyRepository(Protocol):
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


class RateRepository(Protocol):
    async def provider_status(self, provider: ProviderCode) -> dict: ...
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
    async def set_manual(
        self,
        *,
        tenant_id: EntityIdVO,
        pair: CurrencyPair,
        rate: Decimal,
        effective_date: date,
        actor_id: EntityIdVO,
        now: datetime,
    ) -> RateRecord: ...
    async def history(
        self,
        *,
        tenant_id: EntityIdVO,
        provider: ProviderCode,
        pair: CurrencyPair | None,
        limit: int,
        offset: int,
    ) -> Sequence[RateRecord]: ...
