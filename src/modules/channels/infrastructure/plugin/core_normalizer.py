from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit
import nh3
from src.modules.channels.application.port.plugin_services import PluginCallError


def optional_decimal(value: object, warnings: list[str], name: str) -> Decimal | None:
    """Сохраняет точность допустимого числа, отличая 0 от отсутствия."""
    if value is None or value == "":
        return None
    try:
        if isinstance(value, bool):
            raise ValueError("boolean")
        number = Decimal(str(value))
        if (
            not number.is_finite()
            or abs(number) >= Decimal("1e18")
            or number.as_tuple().exponent < -12
        ):
            raise ValueError("range")
        if name in ("price", "sale_price") and number < 0:
            raise ValueError("negative_price")
        return number
    except (ValueError, InvalidOperation):
        warnings.append("invalid_" + name)
        return None


def safe_text(value: object, limit: int, warnings: list[str], name: str) -> str | None:
    """Удаляет HTML и управляющие символы, отмечая усечение входа."""
    if value is None:
        return None
    if not isinstance(value, str):
        warnings.append("invalid_" + name)
        return None
    cleaned = nh3.clean(value, tags=set())
    cleaned = "".join(
        (char for char in cleaned if char.isprintable() or char in ("\n", "\t"))
    )
    if len(cleaned) > limit:
        warnings.append("truncated_" + name)
    return cleaned[:limit]


def safe_url(value: object, warnings: list[str]) -> str | None:
    """Оставляет только HTTPS image URL без credentials и управляющих символов."""
    if value is None or value == "":
        return None
    try:
        if (
            not isinstance(value, str)
            or len(value) > 4096
            or any((not char.isprintable() for char in value))
        ):
            raise ValueError("invalid")
        parsed = urlsplit(value)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username
            or parsed.password
        ):
            raise ValueError("invalid")
        return value
    except ValueError:
        warnings.append("invalid_main_image_url")
        return None


def currency_code(value: object, warnings: list[str]) -> str | None:
    """Не угадывает ISO-код по символу цены или tenant."""
    if (
        isinstance(value, str)
        and len(value) == 3
        and value.isascii()
        and value.isalpha()
        and value.isupper()
    ):
        return value
    warnings.append("currency_unknown")
    return None


def observed_time(
    value: object, warnings: list[str], *, utc_field: bool = False
) -> datetime | None:
    """Применяет UTC только к документированному GMT-полю."""
    if not value:
        return None
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if result.utcoffset() is None:
            if not utc_field:
                raise ValueError("timezone")
            result = result.replace(tzinfo=UTC)
        return result
    except ValueError:
        warnings.append("source_timezone_unknown")
        return None


def native_id(value: object) -> str:
    """Проверяет native integer ID без смешивания с внешним SKU/import ID."""
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PluginCallError("invalid_publication_identity")
    return str(value)


def clean_description(value: object) -> str | None:
    """Санитизирует только ограниченный текст, не копируя весь native документ."""
    return nh3.clean(value[:200000])[:250000] if isinstance(value, str) else None
