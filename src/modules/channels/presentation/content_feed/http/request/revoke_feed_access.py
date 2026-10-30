from pydantic import BaseModel, ConfigDict, Field


class RevokeFeedAccessRequest(BaseModel):
    """Тело отдельного HTTP-сценария revoke_feed_access."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(gt=0, strict=True)
