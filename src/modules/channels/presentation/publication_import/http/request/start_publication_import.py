from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class StartPublicationImportRequest(BaseModel):
    """Задаёт конкретный HTTP-контракт действия с подготовкой."""

    model_config = ConfigDict(extra="forbid")
    preparation_id: UUID
    expected_observed_revision: int = Field(ge=1)
