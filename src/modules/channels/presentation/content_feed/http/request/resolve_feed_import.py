from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ResolveFeedImportRequest(BaseModel):
    """Отдельный HTTP-контракт resolve_feed_import."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(gt=0, strict=True)
    expected_delivery_revision: int = Field(ge=0, strict=True)
    confirm_not_submitted: Literal[True]
