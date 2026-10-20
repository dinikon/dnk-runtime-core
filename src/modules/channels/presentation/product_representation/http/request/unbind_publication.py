from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class UnbindPublicationRequest(BaseModel):
    """Защищает снятие связи от устаревшего выбора строки."""

    model_config = ConfigDict(extra="forbid")
    binding_id: UUID
    expected_revision: int = Field(ge=1)
