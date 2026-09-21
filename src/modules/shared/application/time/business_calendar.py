from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from src.modules.shared.domain.domain_error import DomainError


class BusinessCalendar:
    """Translate instants at the consuming boundary using an explicit timezone."""

    @staticmethod
    def date_at(instant: datetime, timezone_name: str) -> date:
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise DomainError("Business timestamps must include a timezone.")
        return instant.astimezone(ZoneInfo(timezone_name)).date()

    @staticmethod
    def start_of_day(day: date, timezone_name: str) -> datetime:
        return datetime.combine(day, time.min, ZoneInfo(timezone_name)).astimezone(
            timezone.utc
        )

    @classmethod
    def next_day(cls, instant: datetime, timezone_name: str) -> datetime:
        return cls.start_of_day(
            cls.date_at(instant, timezone_name) + timedelta(days=1), timezone_name
        )


__all__ = ["BusinessCalendar"]
