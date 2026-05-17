from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object_feature.value_object import FeatureCodeVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class UpdateObjectFeatureConfigCommand:
    """Команда обновления config feature runtime-объекта."""

    tenant_id: EntityIdVO
    object_id: RuntimeObjectIdVO
    feature_code: FeatureCodeVO
    config: dict[str, Any]


__all__ = ["UpdateObjectFeatureConfigCommand"]
