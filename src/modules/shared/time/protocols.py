from __future__ import annotations

from datetime import datetime
from typing import Protocol


class ClockProtocol(Protocol):
    def now(self) -> datetime: ...
