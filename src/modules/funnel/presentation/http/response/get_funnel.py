from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class StageResponse(BaseModel):
    """Стадия в ответе сценария get."""

    id: UUID
    name: str
    color: str
    position: int
    kind: str
    cards_count: int


class GetFunnelResponse(BaseModel):
    """Конкретный ответ чтения процесса."""

    id: UUID
    model_key: str
    name: str
    is_default: bool
    revision: int
    stages: tuple[StageResponse, ...]
    created_at: datetime
    updated_at: datetime
