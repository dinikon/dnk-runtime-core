from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ConfirmContentUpdateRequest(BaseModel):
    """Описывает конкретный вход ручной операции обновления текстов."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    preview_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
