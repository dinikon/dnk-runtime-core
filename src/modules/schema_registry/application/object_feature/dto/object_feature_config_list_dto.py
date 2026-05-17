from __future__ import annotations

from dataclasses import dataclass

from src.modules.schema_registry.application.object_feature.dto.object_feature_config_dto import (
    ObjectFeatureConfigDTO,
)


@dataclass(frozen=True, slots=True)
class ObjectFeatureConfigListDTO:
    """DTO списка feature configs runtime-объекта."""

    items: list[ObjectFeatureConfigDTO]
    count: int


__all__ = ["ObjectFeatureConfigListDTO"]
