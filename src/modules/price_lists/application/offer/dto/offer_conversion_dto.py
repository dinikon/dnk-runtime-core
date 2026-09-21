from dataclasses import dataclass
from datetime import date
from src.modules.currency.application.conversion.dto.converted_money import (
    ConvertedMoney,
)
from src.modules.price_lists.domain.offer.value_object import OfferStateIdVO


@dataclass(frozen=True, slots=True)
class OfferConversionDTO:
    status: str
    business_date: date | None
    purchase_price: ConvertedMoney | None = None
    rrp: ConvertedMoney | None = None
    error_code: str | None = None

    @classmethod
    def unavailable(cls, code: str, business_date: date | None = None):
        return cls("unavailable", business_date, error_code=code)


@dataclass(frozen=True, slots=True)
class OfferMoneySnapshotDTO:
    state_id: OfferStateIdVO
    conversion: OfferConversionDTO


__all__ = ["OfferConversionDTO", "OfferMoneySnapshotDTO"]
