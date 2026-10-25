from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from src.modules.funnel.application.values import StageProjection
from src.modules.funnel.application.port.read_row import FunnelReadRowDTO


@dataclass(frozen=True, slots=True)
class GetFunnelResultDTO:
    """Конкретный результат чтения get процесса."""

    id: UUID
    model_key: str
    name: str
    is_default: bool
    revision: int
    stages: tuple[StageProjection, ...]
    created_at: datetime
    updated_at: datetime
