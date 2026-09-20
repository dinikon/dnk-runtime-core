import hashlib
import json
from decimal import Decimal
from src.modules.price_lists.domain.offer.value_object.money import ImportPriceVO


def canonical_state_hash(
    *,
    purchase_price: Decimal,
    rrp: Decimal | None,
    currency: str,
    availability: str,
    quantity: int | None,
) -> str:
    payload = {
        "purchase_price": format(ImportPriceVO(purchase_price).value, "f"),
        "rrp": None if rrp is None else format(ImportPriceVO(rrp).value, "f"),
        "currency": currency.upper(),
        "availability": availability,
        "quantity": quantity,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


__all__ = ["canonical_state_hash"]
