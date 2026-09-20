from typing import Any
import re
from src.modules.price_lists.domain.offer.error import InvalidOfferValueError
from src.modules.price_lists.domain.offer.value_object.money import (
    ImportPriceVO,
    QuantityVO,
)
from src.modules.price_lists.domain.offer.value_object.values import OfferValues
from src.modules.price_lists.domain.offer.value_object.availability import (
    normalize_availability,
)


def _path_value(value: Any, selector: str) -> Any:
    current = value
    for part in selector.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _extract(raw: Any, specification: dict[str, Any]) -> Any:
    if "constant" in specification:
        return specification["constant"]
    selectors = specification.get("selectors") or [specification.get("selector")]
    for selector in selectors:
        if selector is None or selector == "":
            continue
        value = None
        if isinstance(raw, dict):
            if isinstance(selector, int):
                row_values = list(raw.values())
                value = (
                    row_values[selector] if 0 <= selector < len(row_values) else None
                )
            else:
                value = raw.get(str(selector), _path_value(raw, str(selector)))
        if value not in (None, ""):
            return value
    return specification.get("default")


def _decimal(value):
    return None if value in (None, "") else ImportPriceVO(value).value


def _integer(value):
    return None if value in (None, "") else QuantityVO(value).value


def normalize_row(
    raw: Any, mapping: dict[str, Any]
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Применяет mapping и проверяет доменные значения одной строки."""
    values: dict[str, Any] = {}
    errors: list[str] = []
    for field, specification in mapping.items():
        specification = specification or {}
        try:
            value = _extract(raw, specification)
            if isinstance(value, str) and specification.get("trim", True):
                value = value.strip()
            replacements = specification.get("replace") or {}
            if isinstance(value, str) and isinstance(replacements, dict):
                for old, new in replacements.items():
                    value = value.replace(str(old), str(new))
            if isinstance(value, str) and specification.get("lower"):
                value = value.lower()
            lookup = specification.get("map") or {}
            if isinstance(lookup, dict):
                value = lookup.get(value, lookup.get(str(value).casefold(), value))
            if specification.get("type") == "decimal" or field in {
                "purchase_price",
                "rrp",
            }:
                value = _decimal(value)
            elif specification.get("type") == "integer" or field == "quantity":
                value = _integer(value)
            if specification.get("required") and value in (None, ""):
                errors.append(f"{field}: required")
            values[field] = value
        except (InvalidOfferValueError, ValueError, TypeError):
            errors.append(f"{field}: invalid value")
            values[field] = None
    for required in ("external_id", "sku", "title", "purchase_price"):
        if values.get(required) in (None, "") and not any(
            error.startswith(f"{required}:") for error in errors
        ):
            errors.append(f"{required}: required")
    currency = str(values.get("currency") or "").strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", currency):
        errors.append("currency: expected ISO 4217 code")
    values["currency"] = currency
    quantity = values.get("quantity")
    values["availability"] = normalize_availability(
        values.get("availability"), quantity
    )
    if not errors:
        try:
            normalized = OfferValues(
                **{key: values.get(key) for key in OfferValues.__dataclass_fields__}
            )
            values = {
                key: getattr(normalized, key)
                for key in OfferValues.__dataclass_fields__
            }
            values["value_hash"] = normalized.value_hash
        except InvalidOfferValueError as exc:
            errors.append(str(exc))
    return values, tuple(errors)


__all__ = ["normalize_row"]
