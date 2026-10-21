from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Self
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from src.modules.channels.domain.error import (
    ChannelsConflictError,
    ChannelsValidationError,
)


@dataclass(slots=True)
class ExportSchedule:
    """Хранит расписание отдельно от настроек доступа к внешнему ресурсу."""

    channel_id: UUID
    enabled: bool
    hour: int
    minute: int
    timezone: str
    revision: int
    next_at: datetime | None

    @classmethod
    def create(cls, channel_id: UUID) -> Self:
        """По умолчанию оставляет только ручной запуск."""
        return cls.restore(channel_id, False, 3, 0, "Europe/Kyiv", 1, None)

    @classmethod
    def restore(
        cls,
        channel_id: UUID,
        enabled: bool,
        hour: int,
        minute: int,
        timezone: str,
        revision: int,
        next_at: datetime | None,
    ) -> Self:
        """Проверяет сохранённую IANA зону и параметры локального времени."""
        try:
            ZoneInfo(timezone)
        except (ZoneInfoNotFoundError, ValueError):
            raise ChannelsValidationError("invalid_export_timezone") from None
        if (
            type(enabled) is not bool
            or not 0 <= hour <= 23
            or not 0 <= minute <= 59
            or revision < 1
            or enabled != (next_at is not None)
            or (next_at is not None and next_at.utcoffset() is None)
        ):
            raise ChannelsValidationError("invalid_export_schedule")
        return cls(channel_id, enabled, hour, minute, timezone, revision, next_at)

    def change(
        self,
        enabled: bool,
        hour: int,
        minute: int,
        timezone: str,
        expected_revision: int,
        now: datetime,
    ) -> None:
        """Изменяет режим с защитой от устаревшего экрана; не меняет generation Connection."""
        if expected_revision != self.revision:
            raise ChannelsConflictError("export_schedule_changed")
        candidate = self.restore(
            self.channel_id,
            enabled,
            hour,
            minute,
            timezone,
            self.revision + 1,
            now if enabled else None,
        )
        self.enabled, self.hour, self.minute, self.timezone, self.revision = (
            candidate.enabled,
            candidate.hour,
            candidate.minute,
            candidate.timezone,
            candidate.revision,
        )
        self.next_at = self.next_after(now) if enabled else None

    def next_after(self, now: datetime) -> datetime:
        """На DST выбирает первый реальный момент, один запуск на календарный день."""
        zone = ZoneInfo(self.timezone)
        local = now.astimezone(zone)
        for delta in range(3):
            day = local.date() + timedelta(days=delta)
            wall = datetime(day.year, day.month, day.day, self.hour, self.minute)
            candidate = wall.replace(tzinfo=zone, fold=0).astimezone(UTC)
            # Пропущенный час нормализуется вперёд, неоднозначный исполняется один раз.
            if candidate > now:
                return candidate
        raise ChannelsValidationError("invalid_export_schedule")

    def consumed(self, now: datetime) -> None:
        """Пропускает устаревшие дни и планирует единственный будущий снимок."""
        if not self.enabled:
            raise ChannelsConflictError("export_schedule_disabled")
        self.next_at = self.next_after(now)
