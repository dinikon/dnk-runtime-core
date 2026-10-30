from pydantic import BaseModel, ConfigDict, Field


class DisableContentFeedRequest(BaseModel):
    """Тело отдельного HTTP-сценария disable_content_feed."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(gt=0, strict=True)
