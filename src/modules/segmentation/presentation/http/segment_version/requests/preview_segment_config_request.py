from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class PreviewSegmentConfigRequestSchema(BaseModel):
    """Request schema for raw segment config preview."""

    config: dict[str, Any]
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
    include_contact_summary: bool = True


__all__ = ["PreviewSegmentConfigRequestSchema"]
