from __future__ import annotations

from typing import Protocol

from src.modules.schema_registry.application.object_feature.command import (
    DisableObjectFeatureCommand,
)
from src.modules.schema_registry.application.object_feature.dto import (
    ObjectFeatureConfigDTO,
)
from src.modules.schema_registry.domain.object_feature.error import (
    ObjectFeatureConfigNotFoundError,
)
from src.modules.schema_registry.domain.object_feature.repository import (
    ObjectFeatureConfigRepositoryProtocol,
)
from src.modules.shared.domain.time import ClockPort


class DisableObjectFeatureUseCaseProtocol(Protocol):
    async def __call__(
        self,
        command: DisableObjectFeatureCommand,
    ) -> ObjectFeatureConfigDTO: ...


class DisableObjectFeatureUseCase:
    """Use case выключения feature config runtime-объекта."""

    def __init__(
        self,
        *,
        repository: ObjectFeatureConfigRepositoryProtocol,
        clock: ClockPort,
    ) -> None:
        """Инициализирует use case repository-портом и clock-портом."""
        self._repository = repository
        self._clock = clock

    async def __call__(
        self,
        command: DisableObjectFeatureCommand,
    ) -> ObjectFeatureConfigDTO:
        """Выключает feature config и возвращает DTO."""
        config = await self._repository.get(
            tenant_id=command.tenant_id,
            object_id=command.object_id,
            feature_code=command.feature_code,
        )
        if config is None:
            raise ObjectFeatureConfigNotFoundError(
                "Object feature config "
                f"'{command.feature_code.value}' was not found for object "
                f"'{command.object_id}'."
            )

        config.disable(now=self._clock.now())
        await self._repository.save(config)
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


__all__ = [
    "DisableObjectFeatureUseCase",
    "DisableObjectFeatureUseCaseProtocol",
]
