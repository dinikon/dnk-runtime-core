from __future__ import annotations

from typing import Protocol

from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object_feature.entity import (
    ObjectFeatureConfigEntity,
)
from src.modules.schema_registry.domain.object_feature.value_object import FeatureCodeVO
from src.modules.shared import EntityIdVO


class ObjectFeatureConfigRepositoryProtocol(Protocol):
    """Порт persistence для feature config runtime-объектов."""

    async def get(
        self,
        *,
        tenant_id: EntityIdVO,
        object_id: RuntimeObjectIdVO,
        feature_code: FeatureCodeVO,
    ) -> ObjectFeatureConfigEntity | None:
        """Возвращает feature config по tenant/object/feature или None."""
        ...

    async def save(self, config: ObjectFeatureConfigEntity) -> None:
        """Сохраняет object feature config."""
        ...

    async def list_by_object(
        self,
        *,
        tenant_id: EntityIdVO,
        object_id: RuntimeObjectIdVO,
    ) -> list[ObjectFeatureConfigEntity]:
        """Возвращает все feature configs runtime-объекта tenant."""
        ...
