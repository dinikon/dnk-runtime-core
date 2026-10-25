from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from src.modules.funnel.application.values import StageProjection
from src.modules.funnel.application.port.read_row import FunnelReadRowDTO


@dataclass(frozen=True, slots=True)
class ListFunnelsResultDTO:
    """Конкретный результат чтения list процесса."""

    items: tuple[FunnelReadRowDTO, ...]
    total: int
    offset: int
    limit: int
