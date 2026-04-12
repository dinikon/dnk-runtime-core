from __future__ import annotations

from datetime import UTC, datetime


class UtcClock:
    """Clock implementation, возвращающий текущее время в UTC."""

    def now(self) -> datetime:
        """Возвращает timezone-aware datetime.now(UTC)."""
        return datetime.now(UTC)
