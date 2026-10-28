from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from src.modules.funnel.application.values import StageProjection
from src.modules.funnel.application.port.read_row import FunnelReadRowDTO


@dataclass(frozen=True, slots=True)
class GetFunnelStageDTO:
    """Стадия карточки определения с актуальным количеством владельцев."""

    id: UUID
    name: str
    color: str
    position: int
    kind: str
    cards_count: int


@dataclass(frozen=True, slots=True)
class GetFunnelResultDTO:
    """Конкретный результат чтения get процесса."""

    id: UUID
    model_key: str
    name: str
    is_default: bool
    revision: int
    stages: tuple[GetFunnelStageDTO, ...]
    created_at: datetime
    updated_at: datetime
