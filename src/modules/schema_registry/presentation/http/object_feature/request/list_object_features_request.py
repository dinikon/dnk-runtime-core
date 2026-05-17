from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ListObjectFeaturesRequestSchema(BaseModel):
    """HTTP request schema списка object feature configs."""

    model_config = ConfigDict(extra="forbid")

    object_id: UUID


__all__ = ["ListObjectFeaturesRequestSchema"]
