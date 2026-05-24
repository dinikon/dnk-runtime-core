from __future__ import annotations

from datetime import datetime
from typing import Protocol


class ClockPort(Protocol):
    """Порт источника текущего времени."""

    def now(self) -> datetime:
        """Возвращает текущий datetime."""
        ...
