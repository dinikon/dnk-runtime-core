from pydantic import BaseModel, ConfigDict, Field


class AttachFeedImportRequest(BaseModel):
    """Отдельный HTTP-контракт attach_feed_import."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(gt=0, strict=True)
    expected_delivery_revision: int = Field(ge=0, strict=True)
    external_id: str = Field(pattern=r"^[0-9]{1,19}$")
