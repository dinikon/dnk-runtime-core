from uuid import UUID
from datetime import datetime
from pydantic import BaseModel


class StageResponse(BaseModel):
    """Стадия в ответе сценария list."""

    id: UUID
    name: str
    color: str
    position: int


class FunnelListItemResponse(BaseModel):
    """Краткое определение процесса."""

    id: UUID
    model_key: str
    name: str
    is_default: bool
    revision: int
    stages: tuple[StageResponse, ...]
    created_at: datetime
    updated_at: datetime


class ListFunnelsResponse(BaseModel):
    """Пагинированная коллекция процессов."""

    items: tuple[FunnelListItemResponse, ...]
    total: int
    offset: int
    limit: int
