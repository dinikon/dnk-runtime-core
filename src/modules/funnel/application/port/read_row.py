from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from src.modules.funnel.application.values import StageProjection


@dataclass(frozen=True, slots=True)
class FunnelReadRowDTO:
    """Собственные поля процесса для сборки read-сценариев."""

    id: UUID
    model_key: str
    name: str
    is_default: bool
    revision: int
    stages: tuple[StageProjection, ...]
    created_at: datetime
    updated_at: datetime
