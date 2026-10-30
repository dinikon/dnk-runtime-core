from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class RequestFeedImportRequest(BaseModel):
    """Отдельный HTTP-контракт request_feed_import."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(gt=0, strict=True)
    expected_delivery_revision: int = Field(ge=0, strict=True)
    request_id: UUID
    force_update: bool = Field(default=False, strict=True)
