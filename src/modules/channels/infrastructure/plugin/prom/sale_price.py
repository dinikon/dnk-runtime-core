from datetime import date, datetime
from decimal import Decimal, localcontext
import re
from src.modules.channels.infrastructure.plugin.core_normalizer import optional_decimal


def normalize_sale_price(
    price: Decimal | None,
    discount: object,
    observed_on: date,
    warnings: list[str],
) -> Decimal | None:
    """Вычисляет действующую скидку Prom без округления и угадывания дат."""
    if discount is None:
        return None
    if not isinstance(discount, dict):
        warnings.append("invalid_sale_price")
        return None
    try:
        start, end = (
            _discount_date(discount.get(key)) for key in ("date_start", "date_end")
        )
        kind = discount.get("type")
        value = optional_decimal(discount.get("value"), [], "sale_price")
        if (
            start > end
            or kind not in ("amount", "percent")
            or value is None
            or price is None
            or (kind == "amount" and value > price)
            or (kind == "percent" and value > 100)
        ):
            raise ValueError("invalid_discount")
    except ValueError:
        warnings.append("invalid_sale_price")
        return None
    if not start <= observed_on <= end or value == 0:
        return None
    with localcontext() as context:
        context.prec = 80
        amount = value if kind == "amount" else price * value / 100
        result = (price - amount).normalize()
    return optional_decimal(result, warnings, "sale_price")


def _discount_date(value: object) -> date:
    """Принимает только документированную календарную дату ДД.ММ.ГГГГ."""
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{2}\.[0-9]{2}\.[0-9]{4}", value
    ):
        raise ValueError("invalid_discount_date")
    return datetime.strptime(value, "%d.%m.%Y").date()
