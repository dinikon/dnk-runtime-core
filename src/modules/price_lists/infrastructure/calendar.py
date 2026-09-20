from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from croniter import croniter
from src.modules.price_lists.domain.price_list.error import PriceListValidationError
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
import uuid6


class CronCalendar:
    """Рассчитывает CRON occurrences в timezone источника."""

    def occurrences(self, expression, timezone, *, after, count=5):
        """Вычисляет следующие календарные запуски с учётом timezone."""
        try:
            zone = ZoneInfo(timezone)
            if not croniter.is_valid(expression):
                raise PriceListValidationError("Invalid CRON expression.")
            iterator = croniter(expression, after.astimezone(zone))
            from datetime import UTC

            values = [
                iterator.get_next(datetime).astimezone(UTC)
                for _ in range(max(count, 2))
            ]
            if any(b - a < timedelta(minutes=15) for a, b in zip(values, values[1:])):
                raise PriceListValidationError(
                    "CRON frequency must be at least 15 minutes."
                )
            return values[:count]
        except (ValueError, TypeError, ZoneInfoNotFoundError):
            raise PriceListValidationError(
                "Invalid CRON expression or timezone."
            ) from None

    def next(self, expression, timezone, *, after):
        """Возвращает первое следующее допустимое occurrence."""
        return self.occurrences(expression, timezone, after=after, count=1)[0]


class IdentifierGenerator:
    """Генерирует UUIDv7 вне domain/application."""

    def new(self):
        """Выдаёт новый идентификатор для команды или агрегата."""
        return EntityIdVO(uuid6.uuid7())


__all__ = ["CronCalendar", "IdentifierGenerator"]
