from typing import Literal

from pydantic import BaseModel


class CreateSegmentDefinitionRequestSchema(BaseModel):
    """Request body for creating Contact segment definition."""

    name: str
    segment_kind: Literal["static", "dynamic"] = "static"
    description: str | None = None


__all__ = ["CreateSegmentDefinitionRequestSchema"]
