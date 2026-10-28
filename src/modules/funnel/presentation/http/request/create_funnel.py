from uuid import UUID
from typing import Literal
from pydantic import Field, BaseModel, ConfigDict


class StrictRequest(BaseModel):
    """Отклоняет неизвестные транспортные поля процесса."""

    model_config = ConfigDict(extra="forbid")


class CreateFunnelStageRequest(StrictRequest):
    """Стадия конкретного входа create процесса."""

    id: UUID | None = None
    client_key: str | None = Field(default=None, max_length=100)
    name: str = Field(min_length=1, max_length=100)
    color: str = Field(default="#64748B", pattern=r"^#[0-9a-fA-F]{6}$")
    kind: Literal["in_progress", "won", "lost"] | None = None


class CreateFunnelRequest(StrictRequest):
    """Полное определение без автоматизаций."""

    name: str = Field(min_length=1, max_length=150)
    stages: tuple[CreateFunnelStageRequest, ...] | None = Field(
        default=None, min_length=3, max_length=50
    )
    model_key: Literal["crm.lead", "crm.deal"]
