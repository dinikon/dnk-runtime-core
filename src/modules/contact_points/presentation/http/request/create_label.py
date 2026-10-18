from typing import Literal

from pydantic import BaseModel, ConfigDict


class CreateLabelRequest(BaseModel):
    """Параметры новой подписи без tenant/actor из клиента."""

    model_config = ConfigDict(extra="forbid")
    type: Literal["phone", "email"]
    name: str
