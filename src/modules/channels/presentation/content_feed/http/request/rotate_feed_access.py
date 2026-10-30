from pydantic import BaseModel, ConfigDict, Field


class RotateFeedAccessRequest(BaseModel):
    """Тело отдельного HTTP-сценария rotate_feed_access."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(gt=0, strict=True)
