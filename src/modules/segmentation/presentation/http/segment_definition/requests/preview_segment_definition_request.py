from uuid import UUID

from pydantic import BaseModel, Field


class PreviewSegmentDefinitionRequestSchema(BaseModel):
    """Request schema for existing segment definition preview."""

    segment_version_id: UUID | None = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    include_contact_summary: bool = True


__all__ = ["PreviewSegmentDefinitionRequestSchema"]
