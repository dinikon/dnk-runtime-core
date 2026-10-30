from pydantic import BaseModel, ConfigDict, Field


class ResumeFeedImportRequest(BaseModel):
    """Отдельный HTTP-контракт resume_feed_import."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(gt=0, strict=True)
    expected_delivery_revision: int = Field(ge=0, strict=True)
