from __future__ import annotations

from src.modules.schema_registry.application.object_feature.dto import (
    ObjectFeatureConfigDTO,
    ObjectFeatureConfigListDTO,
)
from src.modules.schema_registry.application.object_feature.query import (
    ListObjectFeaturesQuery,
)
from src.modules.schema_registry.domain.object_feature.repository import (
    ObjectFeatureConfigRepositoryProtocol,
)


class ListObjectFeaturesUseCase:
    """Use case списка feature configs runtime-объекта."""

    def __init__(self, repository: ObjectFeatureConfigRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом object feature config."""
        self._repository = repository

    async def __call__(
        self,
        query: ListObjectFeaturesQuery,
    ) -> ObjectFeatureConfigListDTO:
        """Возвращает список feature configs runtime-объекта."""
        configs = await self._repository.list_by_object(
            tenant_id=query.tenant_id,
            object_id=query.object_id,
        )
        return ObjectFeatureConfigListDTO(
            items=[
                ObjectFeatureConfigDTO(
                    id=config.id.uuid,
                    created_at=config.created_at,
                    updated_at=config.updated_at,
                    object_id=config.object_id.uuid,
                    feature_code=config.feature_code.value,
                    kind=config.kind.value,
                    status=config.status.value,
                    config=dict(config.config),
                    is_locked=config.is_locked,
                    locked_reason=config.locked_reason,
                )
                for config in configs
            ],
            count=len(configs),
        )


__all__ = ["ListObjectFeaturesUseCase"]
