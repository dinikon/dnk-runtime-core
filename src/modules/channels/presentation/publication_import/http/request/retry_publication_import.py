from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class RetryPublicationImportRequest(BaseModel):
    """Задаёт конкретный HTTP-контракт действия с подготовкой."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
