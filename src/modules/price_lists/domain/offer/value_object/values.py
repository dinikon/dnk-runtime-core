from dataclasses import dataclass
from decimal import Decimal
import re
from src.modules.price_lists.domain.offer.error import InvalidOfferValueError
from src.modules.price_lists.domain.offer.value_object.money import MoneyVO, QuantityVO
from src.modules.price_lists.domain.offer.value_object.availability import (
    normalize_availability,
)
from src.modules.price_lists.domain.offer.value_object.state_hash import (
    canonical_state_hash,
)


@dataclass(slots=True, frozen=True)
class OfferValues:
    """Проверенные атрибуты предложения из источника."""

    external_id: str
    sku: str
    title: str
    purchase_price: Decimal
    rrp: Decimal | None
    currency: str
    availability: str
    quantity: int | None

    def __post_init__(self):
        for name in ("external_id", "sku", "title"):
            value = getattr(self, name)
            if value is None or not 1 <= len(str(value).strip()) <= 255:
                raise InvalidOfferValueError(f"{name}: expected 1 to 255 characters")
            object.__setattr__(self, name, str(value).strip())
        object.__setattr__(self, "purchase_price", MoneyVO(self.purchase_price).value)
        if self.rrp is not None:
            object.__setattr__(self, "rrp", MoneyVO(self.rrp).value)
        if self.quantity is not None:
            object.__setattr__(self, "quantity", QuantityVO(self.quantity).value)
        currency = str(self.currency).strip().upper()
        if not re.fullmatch("[A-Z]{3}", currency):
            raise InvalidOfferValueError("currency: expected ISO 4217 code")
        object.__setattr__(self, "currency", currency)
        object.__setattr__(
            self,
            "availability",
            normalize_availability(self.availability, self.quantity),
        )

    @property
    def value_hash(self) -> str:
        """Канонический отпечаток цены и наличия."""
        return canonical_state_hash(
            purchase_price=self.purchase_price,
            rrp=self.rrp,
            currency=self.currency,
            availability=self.availability,
            quantity=self.quantity,
        )


__all__ = ["OfferValues"]
