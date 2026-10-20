from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class BindExistingPublicationRequest(BaseModel):
    """Принимает явную цель и ожидаемую версию существующей пары."""

    model_config = ConfigDict(extra="forbid")
    catalog_item_id: UUID
    expected_revision: int | None = Field(default=None, ge=1)
