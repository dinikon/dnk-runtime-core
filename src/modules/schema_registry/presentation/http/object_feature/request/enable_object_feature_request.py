from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EnableObjectFeatureRequestSchema(BaseModel):
    """HTTP request schema включения object feature."""

    model_config = ConfigDict(extra="forbid")

    object_id: UUID
    feature_code: str
    config: dict[str, Any] = Field(default_factory=dict)


__all__ = ["EnableObjectFeatureRequestSchema"]
