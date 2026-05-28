from pydantic import BaseModel, Field


class PreviewSegmentVersionRequestSchema(BaseModel):
    """Request schema for exact segment version preview."""

    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    include_contact_summary: bool = True


__all__ = ["PreviewSegmentVersionRequestSchema"]
