from pydantic import BaseModel


class UpdateSegmentDefinitionRequestSchema(BaseModel):
    """Request body for updating Contact segment definition."""

    name: str | None = None
    description: str | None = None


__all__ = ["UpdateSegmentDefinitionRequestSchema"]
