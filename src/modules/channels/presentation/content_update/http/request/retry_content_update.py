from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class RetryContentUpdateRequest(BaseModel):
    """Описывает конкретный вход ручной операции обновления текстов."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
