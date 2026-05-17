from __future__ import annotations

from typing import Protocol

from src.modules.schema_registry.application.object_feature.dto import (
    ObjectFeatureConfigDTO,
)
from src.modules.schema_registry.application.object_feature.query import (
    GetObjectFeatureQuery,
)
from src.modules.schema_registry.domain.object_feature.error import (
    ObjectFeatureConfigNotFoundError,
)
from src.modules.schema_registry.domain.object_feature.repository import (
    ObjectFeatureConfigRepositoryProtocol,
)


class GetObjectFeatureConfigUseCaseProtocol(Protocol):
    async def __call__(
        self,
        query: GetObjectFeatureQuery,
    ) -> ObjectFeatureConfigDTO: ...


class GetObjectFeatureConfigUseCase:
    """Use case чтения feature config runtime-объекта."""

    def __init__(self, repository: ObjectFeatureConfigRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом object feature config."""
        self._repository = repository

    async def __call__(self, query: GetObjectFeatureQuery) -> ObjectFeatureConfigDTO:
        """Возвращает feature config или поднимает not-found ошибку."""
        feature_config = await self._repository.get(
            tenant_id=query.tenant_id,
            object_id=query.object_id,
            feature_code=query.feature_code,
        )

        if feature_config is None:
            raise ObjectFeatureConfigNotFoundError(...)

        dto_config = feature_config.config.copy()

        return ObjectFeatureConfigDTO(
            id=feature_config.id.uuid,
            created_at=feature_config.created_at,
            updated_at=feature_config.updated_at,
            object_id=feature_config.object_id.uuid,
            feature_code=feature_config.feature_code.value,
            kind=feature_config.kind.value,
            status=feature_config.status.value,
            config=dto_config,
            is_locked=feature_config.is_locked,
            locked_reason=feature_config.locked_reason,
        )


__all__ = [
    "GetObjectFeatureConfigUseCase",
    "GetObjectFeatureConfigUseCaseProtocol",
]
