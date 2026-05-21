from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ObjectFeatureRequestSchema(BaseModel):
    """HTTP request schema чтения/выключения object feature."""

    model_config = ConfigDict(extra="forbid")

    object_id: UUID
    feature_code: str


__all__ = ["ObjectFeatureRequestSchema"]
