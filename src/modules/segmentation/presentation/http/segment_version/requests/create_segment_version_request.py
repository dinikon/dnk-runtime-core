from typing import Any

from pydantic import BaseModel


class CreateSegmentVersionRequestSchema(BaseModel):
    """Request body for creating draft segment version."""

    config: dict[str, Any]


__all__ = ["CreateSegmentVersionRequestSchema"]
