from uuid import UUID
from typing import Literal
from pydantic import Field, BaseModel, ConfigDict


class StrictRequest(BaseModel):
    """Отклоняет неизвестные транспортные поля процесса."""

    model_config = ConfigDict(extra="forbid")


class UpdateFunnelStageRequest(StrictRequest):
    """Стадия конкретного входа update процесса."""

    id: UUID | None = None
    client_key: str | None = Field(default=None, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    color: Literal["neutral", "blue", "green", "amber", "red", "violet"] = "neutral"


class UpdateFunnelRequest(StrictRequest):
    """Полное определение без автоматизаций."""

    name: str = Field(min_length=1, max_length=150)
    stages: tuple[UpdateFunnelStageRequest, ...] = Field(min_length=1, max_length=50)
    expected_revision: int = Field(ge=1)
