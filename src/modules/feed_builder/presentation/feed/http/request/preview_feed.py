from pydantic import BaseModel, ConfigDict, Field


class PreviewFeedRequest(BaseModel):
    """Указывает версию сохранённой схемы, которую читает предпросмотр."""

    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(strict=True, ge=1, le=2**63 - 1)
