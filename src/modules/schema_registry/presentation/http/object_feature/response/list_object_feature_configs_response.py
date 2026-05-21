from __future__ import annotations

from pydantic import BaseModel

from src.modules.schema_registry.presentation.http.object_feature.response.object_feature_config_response import (
    ObjectFeatureConfigResponseSchema,
)


class ListObjectFeatureConfigsResponseSchema(BaseModel):
    """HTTP response schema списка feature configs runtime-объекта."""

    items: list[ObjectFeatureConfigResponseSchema]
    count: int


__all__ = ["ListObjectFeatureConfigsResponseSchema"]
