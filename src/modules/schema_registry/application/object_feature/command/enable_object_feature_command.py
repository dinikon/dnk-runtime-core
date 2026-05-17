from __future__ import annotations

from dataclasses import dataclass

from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object_feature.value_object import FeatureCodeVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class EnableObjectFeatureCommand:
    """Команда включения feature config runtime-объекта."""

    tenant_id: EntityIdVO
    object_id: RuntimeObjectIdVO
    feature_code: FeatureCodeVO


__all__ = ["EnableObjectFeatureCommand"]
