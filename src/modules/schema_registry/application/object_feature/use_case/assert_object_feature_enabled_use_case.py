from __future__ import annotations

from typing import Protocol

from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object_feature.error import (
    ObjectFeatureConfigNotFoundError,
)
from src.modules.schema_registry.domain.object_feature.repository import (
    ObjectFeatureConfigRepositoryProtocol,
)
from src.modules.schema_registry.domain.object_feature.value_object import FeatureCodeVO
from src.modules.shared import EntityIdVO


class AssertObjectFeatureEnabledUseCaseProtocol(Protocol):
    async def __call__(
        self,
        *,
        tenant_id: EntityIdVO,
        object_id: RuntimeObjectIdVO,
        feature_code: str | FeatureCodeVO,
    ) -> None: ...


class AssertObjectFeatureEnabledUseCase:
    """Use case проверки, что feature runtime-объекта включен."""

    def __init__(self, repository: ObjectFeatureConfigRepositoryProtocol) -> None:
        """Инициализирует use case repository-портом object feature config."""
        self._repository = repository

    async def __call__(
        self,
        *,
        tenant_id: EntityIdVO,
        object_id: RuntimeObjectIdVO,
        feature_code: str | FeatureCodeVO,
    ) -> None:
        """Проверяет enabled-статус feature config для внешних модулей."""
        feature_code_vo = (
            feature_code
            if isinstance(feature_code, FeatureCodeVO)
            else FeatureCodeVO(feature_code)
        )
        config = await self._repository.get(
            tenant_id=tenant_id,
            object_id=object_id,
            feature_code=feature_code_vo,
        )
        if config is None:
            raise ObjectFeatureConfigNotFoundError(
                "Object feature config "
                f"'{feature_code_vo.value}' was not found for object "
                f"'{object_id}'."
            )

        config.assert_enabled()


__all__ = [
    "AssertObjectFeatureEnabledUseCase",
    "AssertObjectFeatureEnabledUseCaseProtocol",
]
