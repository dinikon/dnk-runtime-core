from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class StartContentUpdateRequest(BaseModel):
    """Описывает конкретный вход ручной операции обновления текстов."""

    model_config = ConfigDict(extra="forbid")
    run_id: UUID
    publication_ids: list[UUID] = Field(min_length=1, max_length=50)
