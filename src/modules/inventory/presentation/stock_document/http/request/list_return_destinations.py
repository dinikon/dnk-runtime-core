from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class ListReturnDestinationsRequest(BaseModel):
    """Проверяет транспортные параметры поиска локаций назначения."""

    model_config = ConfigDict(extra="forbid")
    search: str | None = Field(default=None, max_length=200)
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)
    location_id: UUID | None = None
