from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class SetProductTagsRequest(BaseModel):
    """Полная замена tags в отдельном HTTP-сценарии."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    tag_ids: tuple[UUID, ...]
