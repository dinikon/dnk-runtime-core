from __future__ import annotations
from src.modules.currency.domain.exchange_rate.value_object.currency_pair import (
    CurrencyPair,
)
from src.modules.currency.domain.manual_rate.entity import ManualExchangeRate
from src.modules.currency.domain.manual_rate.value_object.id import (
    ManualExchangeRateIdVO,
)
from src.modules.currency.domain.provider_rate.entity import ProviderRate
from src.modules.currency.domain.provider_rate.value_object.id import ProviderRateIdVO
from src.modules.shared.domain.value_object.currency import CurrencyCodeVO as Code
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


def rate_record(row, provider):
    """Map a revision to the entity owned by its storage aggregate."""
    common = dict(
        pair=CurrencyPair(Code(row["source_currency"]), Code(row["target_currency"])),
        rate=row["rate"],
        effective_date=row["effective_date"],
        provider_code=provider,
        revision=row["revision"],
        is_current=row["is_current"],
        calculated_date=row.get("calculated_date"),
        created_at=row["created_at"],
    )
    if str(provider) == "MANUAL":
        return ManualExchangeRate(
            id=ManualExchangeRateIdVO.from_value(row["id"]),
            created_by=EntityIdVO.from_value(row["created_by"]),
            **common,
        )
    return ProviderRate(
        id=ProviderRateIdVO.from_value(row["id"]),
        published_at=row.get("published_at"),
        fetched_at=row["fetched_at"],
        **common,
    )


__all__ = ["rate_record"]
