from __future__ import annotations
from collections.abc import Sequence
from datetime import date
from typing import Protocol
from src.modules.currency.application.conversion.dto.conversion_request import (
    ConversionRequest,
)
from src.modules.currency.application.conversion.dto.converted_money import (
    ConvertedMoney,
)
from src.modules.currency.application.conversion.dto.rate_quote_dto import RateQuoteDTO
from src.modules.currency.application.conversion.dto.unavailable_conversion import (
    UnavailableConversion,
)
from src.modules.currency.domain.conversion.value_object.conversion_purpose import (
    ConversionPurpose,
)
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.domain.value_object.money import Money


class CurrencyFacade(Protocol):
    """Dated currency calculations available to other application contexts."""

    async def get_functional_currency(
        self, *, tenant_id: EntityIdVO, business_date: date
    ) -> CurrencyCodeVO: ...

    async def resolve_rate(
        self,
        *,
        tenant_id: EntityIdVO,
        source: CurrencyCodeVO,
        target: CurrencyCodeVO,
        date: date,
    ) -> RateQuoteDTO: ...

    async def convert(
        self,
        *,
        tenant_id: EntityIdVO,
        money: Money,
        target: CurrencyCodeVO,
        date: date,
        purpose: ConversionPurpose = ConversionPurpose.CALCULATION,
        precision: int | None = None,
    ) -> ConvertedMoney: ...

    async def convert_to_functional(
        self,
        *,
        tenant_id: EntityIdVO,
        money: Money,
        business_date: date,
        purpose: ConversionPurpose = ConversionPurpose.CALCULATION,
        precision: int | None = None,
    ) -> ConvertedMoney: ...

    async def convert_many(
        self,
        *,
        tenant_id: EntityIdVO,
        items: Sequence[ConversionRequest],
        operation_id: EntityIdVO | None = None,
    ) -> list[ConvertedMoney | UnavailableConversion]: ...


__all__ = ["CurrencyFacade"]
