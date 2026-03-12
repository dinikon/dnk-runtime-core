from __future__ import annotations

from datetime import UTC, datetime


class UtcSystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)
