from __future__ import annotations

CUSTOM_OBJECT_PREFIX = "c_"


def has_custom_object_prefix(value: str) -> bool:
    """Проверяет, зарезервировано ли имя под custom object namespace."""
    return value.strip().startswith(CUSTOM_OBJECT_PREFIX)


def with_custom_object_prefix(value: str) -> str:
    """Возвращает trim-имя с custom object prefix, не добавляя его повторно."""
    normalized = value.strip()
    if not normalized or has_custom_object_prefix(normalized):
        return normalized
    return f"{CUSTOM_OBJECT_PREFIX}{normalized}"


def normalize_custom_object_names(
    *,
    singular_name: str,
    plural_name: str,
) -> tuple[str, str]:
    """Нормализует singular/plural имена custom object для metadata и DDL."""
    return (
        with_custom_object_prefix(singular_name),
        with_custom_object_prefix(plural_name),
    )


__all__ = [
    "CUSTOM_OBJECT_PREFIX",
    "has_custom_object_prefix",
    "normalize_custom_object_names",
    "with_custom_object_prefix",
]
