from datetime import UTC, datetime

from src.modules.inventory.domain.valuation_posting.error import (
    ValuationPostingTimeError,
)


def normalize_valuation_posting_time(value: datetime) -> datetime:
    """Нормализует явное aware-время стоимостного проведения в UTC без чтения часов."""
    if not isinstance(value, datetime):
        raise ValuationPostingTimeError("Нужен datetime с часовым поясом.")
    try:
        if value.utcoffset() is None:
            raise ValuationPostingTimeError(
                "Время регистрации стоимости должно содержать часовой пояс."
            )
        return value.astimezone(UTC)
    except (ValueError, OverflowError) as exc:
        raise ValuationPostingTimeError(
            "Время регистрации стоимости невозможно представить в UTC."
        ) from exc
