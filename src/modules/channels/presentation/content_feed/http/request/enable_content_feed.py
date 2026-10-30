from pydantic import BaseModel, ConfigDict, Field


class EnableContentFeedRequest(BaseModel):
    """Тело отдельного HTTP-сценария enable_content_feed."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(gt=0, strict=True)
