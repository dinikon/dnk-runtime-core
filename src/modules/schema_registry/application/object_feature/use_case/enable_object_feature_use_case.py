from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

from src.modules.schema_registry.application.object_feature.command import (
    EnableObjectFeatureCommand,
)
from src.modules.schema_registry.application.object_feature.dto import (
    ObjectFeatureConfigDTO,
)
from src.modules.schema_registry.domain.object_feature.entity import (
    ObjectFeatureConfigEntity,
)
from src.modules.schema_registry.domain.object_feature.repository import (
    ObjectFeatureConfigRepositoryProtocol,
)
from src.modules.schema_registry.domain.object_feature.value_object import (
    ObjectFeatureConfigIdVO,
    ObjectFeatureKind,
)
from src.modules.shared.kernel.time.ports import ClockPort


class EnableObjectFeatureUseCaseProtocol(Protocol):
    async def __call__(
        self,
        command: EnableObjectFeatureCommand,
    ) -> ObjectFeatureConfigDTO: ...


class EnableObjectFeatureUseCase:
    """Use case включения feature config runtime-объекта."""

    def __init__(
        self,
        *,
        repository: ObjectFeatureConfigRepositoryProtocol,
        clock: ClockPort,
        id_provider: Callable[[], ObjectFeatureConfigIdVO],
    ) -> None:
        """Инициализирует use case repository-портом и clock-портом."""
        self._repository = repository
        self._clock = clock
        self._id_provider = id_provider

    async def __call__(
        self,
        command: EnableObjectFeatureCommand,
    ) -> ObjectFeatureConfigDTO:
        """Включает feature config и возвращает DTO."""
        now = self._clock.now()
        config = await self._repository.get(
            tenant_id=command.tenant_id,
            object_id=command.object_id,
            feature_code=command.feature_code,
        )
        if config is None:
            config = ObjectFeatureConfigEntity.create(
                id_=self._id_provider(),
                now=now,
                tenant_id=command.tenant_id,
                object_id=command.object_id,
                feature_code=command.feature_code,
                kind=ObjectFeatureKind.CUSTOM,
                config=command.config,
            )
        else:
            config.update_config(now=now, config=command.config)

        config.enable(now=now)
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
    "EnableObjectFeatureUseCase",
    "EnableObjectFeatureUseCaseProtocol",
]
