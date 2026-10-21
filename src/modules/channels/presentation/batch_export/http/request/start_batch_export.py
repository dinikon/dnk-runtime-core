from uuid import UUID
from typing import Literal
from pydantic import BaseModel, ConfigDict


class StartBatchExportRequest(BaseModel):
    """Передаёт стабильный идентификатор подтверждённого пользователем запуска."""

    model_config = ConfigDict(extra="forbid")
    run_id: UUID
    delivery_mode: Literal["provider", "file"] = "provider"
