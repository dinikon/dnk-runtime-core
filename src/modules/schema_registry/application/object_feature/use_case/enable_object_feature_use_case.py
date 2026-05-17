from __future__ import annotations

from collections.abc import Callable

from src.modules.schema_registry.application.object_feature.command import (
    EnableObjectFeatureCommand,
)
from src.modules.schema_registry.application.object_feature.dto import (
    ObjectFeatureConfigDTO,
)
from src.modules.schema_registry.application.object_feature.use_case.get_object_feature_config_use_case import (
    GetObjectFeatureConfigUseCase,
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
        return GetObjectFeatureConfigUseCase._to_dto(config)


__all__ = ["EnableObjectFeatureUseCase"]
