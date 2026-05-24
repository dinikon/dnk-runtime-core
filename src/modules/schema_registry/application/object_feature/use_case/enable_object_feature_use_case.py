from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Any

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
from src.modules.shared.domain.time import ClockPort


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
        now = self._clock.now()

        feature_config = await self._repository.get(
            tenant_id=command.tenant_id,
            object_id=command.object_id,
            feature_code=command.feature_code,
        )

        command_config = command.config

        if feature_config is None:
            feature_config = ObjectFeatureConfigEntity.create(
                id_=self._id_provider(),
                now=now,
                tenant_id=command.tenant_id,
                object_id=command.object_id,
                feature_code=command.feature_code,
                kind=ObjectFeatureKind.CUSTOM,
                config=command_config,
            )
        else:
            feature_config.update_config(now=now, config=command_config)

        feature_config.enable(now=now)

        await self._repository.save(feature_config)

        dto_config = dict(feature_config.config)

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
    "EnableObjectFeatureUseCase",
    "EnableObjectFeatureUseCaseProtocol",
]
