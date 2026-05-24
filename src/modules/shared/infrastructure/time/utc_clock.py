from __future__ import annotations

from datetime import UTC, datetime

from src.modules.shared.domain.time import ClockPort


class UtcClock(ClockPort):
    """Clock implementation, возвращающий текущее время в UTC."""

    def now(self) -> datetime:
        """Возвращает timezone-aware datetime.now(UTC)."""
        return datetime.now(UTC)
