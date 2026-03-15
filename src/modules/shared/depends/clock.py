from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from src.modules.shared.infrastructure.time.utc_clock import UtcClock
from src.modules.shared.kernel.time.ports import ClockPort

default_clock: ClockPort = UtcClock()


def get_clock(request: Request) -> ClockPort:
    from_state = getattr(request.app.state, "clock", None)
    if from_state is not None:
        return from_state
    return default_clock


ClockDep = Annotated[ClockPort, Depends(get_clock)]

__all__ = ["ClockDep", "default_clock", "get_clock"]

