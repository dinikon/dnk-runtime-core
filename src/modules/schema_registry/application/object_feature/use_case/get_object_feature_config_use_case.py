from __future__ import annotations

from src.modules.schema_registry.application.object_feature.dto import (
    ObjectFeatureConfigDTO,
)
from src.modules.schema_registry.application.object_feature.query import (
    GetObjectFeatureQuery,
)
from src.modules.schema_registry.domain.object_feature.entity import (
    ObjectFeatureConfigEntity,
)
from src.modules.schema_registry.domain.object_feature.error import (
    ObjectFeatureConfigNotFoundError,
)
from src.modules.schema_registry.domain.object_feature.repository import (
    ObjectFeatureConfigRepositoryProtocol,
)


class GetObjectFeatureConfigUseCase:
    """Use case чтения feature config runtime-объекта."""

    def __init__(self, repository: ObjectFeatureConfigRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом object feature config."""
        self._repository = repository

    async def __call__(self, query: GetObjectFeatureQuery) -> ObjectFeatureConfigDTO:
        """Возвращает feature config или поднимает not-found ошибку."""
        config = await self._repository.get(
            tenant_id=query.tenant_id,
            object_id=query.object_id,
            feature_code=query.feature_code,
        )
        if config is None:
            raise ObjectFeatureConfigNotFoundError(
                "Object feature config "
                f"'{query.feature_code.value}' was not found for object "
                f"'{query.object_id}'."
            )
        return self._to_dto(config)

    @staticmethod
    def _to_dto(config: ObjectFeatureConfigEntity) -> ObjectFeatureConfigDTO:
        """Мапит ObjectFeatureConfigEntity в DTO."""
        return ObjectFeatureConfigDTO(
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


__all__ = ["GetObjectFeatureConfigUseCase"]
