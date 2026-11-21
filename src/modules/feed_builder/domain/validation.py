"""Общие чистые проверки значений агрегатов FeedBuilder."""

from datetime import datetime
from src.modules.feed_builder.domain.error import FeedBuilderDomainError


def require_datetime(value: datetime, *, error: type[FeedBuilderDomainError]) -> None:
    """Требует дату с явной временной зоной без обращения к часам."""
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise error("Требуется дата с временной зоной.")


def require_integer(
    value: int, *, minimum: int, error: type[FeedBuilderDomainError]
) -> None:
    """Проверяет целое значение и нижнюю границу, исключая bool."""
    if type(value) is not int or value < minimum:
        raise error(f"Требуется целое число не меньше {minimum}.")


def require_text(
    value: str, *, maximum: int, error: type[FeedBuilderDomainError]
) -> None:
    """Проверяет непустую ограниченную строку без управляющих символов."""
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > maximum
        or not value.isprintable()
    ):
        raise error("Требуется непустая строка допустимой длины и состава.")
