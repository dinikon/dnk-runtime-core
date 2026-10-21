from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class RepresentationExportRefRequest(BaseModel):
    """Передаёт конкретную связь с ожидаемой версией."""

    model_config = ConfigDict(extra="forbid")
    representation_id: UUID
    expected_revision: int = Field(ge=1)


class SetPublicationExportRequest(BaseModel):
    """Описывает явное разрешение выбранных связей, независимо от флага Channel."""

    model_config = ConfigDict(extra="forbid")
    enabled: bool
    items: list[RepresentationExportRefRequest] = Field(min_length=1, max_length=100)
