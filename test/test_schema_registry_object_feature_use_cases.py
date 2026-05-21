from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from src.modules.schema_registry.application.object_feature.command import (
    DisableObjectFeatureCommand,
    EnableObjectFeatureCommand,
    UpdateObjectFeatureConfigCommand,
)
from src.modules.schema_registry.application.object_feature.query import (
    GetObjectFeatureQuery,
    ListObjectFeaturesQuery,
)
from src.modules.schema_registry.application.object_feature.use_case import (
    AssertObjectFeatureEnabledUseCase,
    DisableObjectFeatureUseCase,
    EnableObjectFeatureUseCase,
    GetObjectFeatureConfigUseCase,
    ListObjectFeaturesUseCase,
    UpdateObjectFeatureConfigUseCase,
)
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object_feature.entity import (
    ObjectFeatureConfigEntity,
)
from src.modules.schema_registry.domain.object_feature.error import (
    ObjectFeatureConfigNotFoundError,
    ObjectFeatureNotEnabledError,
)
from src.modules.schema_registry.domain.object_feature.value_object import (
    FeatureCodeVO,
    ObjectFeatureConfigIdVO,
    ObjectFeatureStatus,
)
from src.modules.shared import EntityIdVO


class _ClockStub:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class _RepositoryStub:
    def __init__(
        self,
        *,
        config: ObjectFeatureConfigEntity | None = None,
        configs: list[ObjectFeatureConfigEntity] | None = None,
    ) -> None:
        self.config = config
        self.configs = configs or []
        self.saved: list[ObjectFeatureConfigEntity] = []

    async def get(self, **_kwargs) -> ObjectFeatureConfigEntity | None:
        return self.config

    async def save(self, config: ObjectFeatureConfigEntity) -> None:
        self.saved.append(config)
        self.config = config

    async def list_by_object(self, **_kwargs) -> list[ObjectFeatureConfigEntity]:
        return list(self.configs)


def _entity(
    *,
    tenant_id: EntityIdVO | None = None,
    object_id: RuntimeObjectIdVO | None = None,
    config_id: ObjectFeatureConfigIdVO | None = None,
    now: datetime | None = None,
    status: ObjectFeatureStatus = ObjectFeatureStatus.DISABLED,
    config: dict[str, object] | None = None,
) -> ObjectFeatureConfigEntity:
    timestamp = now or datetime.now(UTC)
    return ObjectFeatureConfigEntity.create(
        id_=config_id or ObjectFeatureConfigIdVO.from_value(uuid4()),
        now=timestamp,
        tenant_id=tenant_id or EntityIdVO.from_value(uuid4()),
        object_id=object_id or RuntimeObjectIdVO.from_value(uuid4()),
        feature_code=FeatureCodeVO("CONTACT_POINT"),
        status=status,
        config=config or {},
    )


class SchemaRegistryObjectFeatureUseCaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_enable_creates_config_when_it_does_not_exist(self) -> None:
        now = datetime.now(UTC)
        tenant_id = EntityIdVO.from_value(uuid4())
        object_id = RuntimeObjectIdVO.from_value(uuid4())
        config_id = ObjectFeatureConfigIdVO.from_value(uuid4())
        repository = _RepositoryStub()
        use_case = EnableObjectFeatureUseCase(
            repository=repository,
            clock=_ClockStub(now),
            id_provider=lambda: config_id,
        )

        dto = await use_case(
            EnableObjectFeatureCommand(
                tenant_id=tenant_id,
                object_id=object_id,
                feature_code=FeatureCodeVO("CONTACT_POINT"),
                config={"schema": "contact"},
            )
        )

        self.assertEqual(dto.id, config_id.uuid)
        self.assertEqual(dto.status, "enabled")
        self.assertEqual(dto.config, {"schema": "contact"})
        self.assertEqual(repository.saved[0].tenant_id, tenant_id)

    async def test_enable_updates_config_when_it_exists(self) -> None:
        now = datetime.now(UTC)
        entity = _entity(now=now, config={"old": True})
        repository = _RepositoryStub(config=entity)
        use_case = EnableObjectFeatureUseCase(
            repository=repository,
            clock=_ClockStub(now + timedelta(seconds=1)),
            id_provider=lambda: ObjectFeatureConfigIdVO.from_value(uuid4()),
        )

        dto = await use_case(
            EnableObjectFeatureCommand(
                tenant_id=entity.tenant_id,
                object_id=entity.object_id,
                feature_code=entity.feature_code,
                config={"new": True},
            )
        )

        self.assertEqual(dto.id, entity.id.uuid)
        self.assertEqual(dto.status, "enabled")
        self.assertEqual(dto.config, {"new": True})

    async def test_disable_turns_config_off(self) -> None:
        entity = _entity(status=ObjectFeatureStatus.ENABLED)
        repository = _RepositoryStub(config=entity)
        use_case = DisableObjectFeatureUseCase(
            repository=repository,
            clock=_ClockStub(datetime.now(UTC)),
        )

        dto = await use_case(
            DisableObjectFeatureCommand(
                tenant_id=entity.tenant_id,
                object_id=entity.object_id,
                feature_code=entity.feature_code,
            )
        )

        self.assertEqual(dto.status, "disabled")
        self.assertEqual(repository.saved[0].status, ObjectFeatureStatus.DISABLED)

    async def test_update_config_updates_config(self) -> None:
        entity = _entity(status=ObjectFeatureStatus.ENABLED)
        repository = _RepositoryStub(config=entity)
        use_case = UpdateObjectFeatureConfigUseCase(
            repository=repository,
            clock=_ClockStub(datetime.now(UTC)),
        )

        dto = await use_case(
            UpdateObjectFeatureConfigCommand(
                tenant_id=entity.tenant_id,
                object_id=entity.object_id,
                feature_code=entity.feature_code,
                config={"fields": ["email"]},
            )
        )

        self.assertEqual(dto.config, {"fields": ["email"]})
        self.assertEqual(repository.saved[0].config, {"fields": ["email"]})

    async def test_get_returns_dto(self) -> None:
        entity = _entity(status=ObjectFeatureStatus.ENABLED, config={"x": 1})
        use_case = GetObjectFeatureConfigUseCase(_RepositoryStub(config=entity))

        dto = await use_case(
            GetObjectFeatureQuery(
                tenant_id=entity.tenant_id,
                object_id=entity.object_id,
                feature_code=entity.feature_code,
            )
        )

        self.assertEqual(dto.id, entity.id.uuid)
        self.assertEqual(dto.config, {"x": 1})

    async def test_list_returns_list_dto(self) -> None:
        first = _entity(status=ObjectFeatureStatus.ENABLED)
        second = _entity(status=ObjectFeatureStatus.DISABLED)
        use_case = ListObjectFeaturesUseCase(_RepositoryStub(configs=[first, second]))

        dto = await use_case(
            ListObjectFeaturesQuery(
                tenant_id=first.tenant_id,
                object_id=first.object_id,
            )
        )

        self.assertEqual(dto.count, 2)
        self.assertEqual(
            [item.id for item in dto.items], [first.id.uuid, second.id.uuid]
        )

    async def test_assert_enabled_success(self) -> None:
        entity = _entity(status=ObjectFeatureStatus.ENABLED)
        use_case = AssertObjectFeatureEnabledUseCase(_RepositoryStub(config=entity))

        result = await use_case(
            tenant_id=entity.tenant_id,
            object_id=entity.object_id,
            feature_code=FeatureCodeVO("CONTACT_POINT"),
        )

        self.assertIsNone(result)

    async def test_assert_enabled_not_found(self) -> None:
        use_case = AssertObjectFeatureEnabledUseCase(_RepositoryStub(config=None))

        with self.assertRaises(ObjectFeatureConfigNotFoundError):
            await use_case(
                tenant_id=EntityIdVO.from_value(uuid4()),
                object_id=RuntimeObjectIdVO.from_value(uuid4()),
                feature_code="CONTACT_POINT",
            )

    async def test_assert_enabled_disabled(self) -> None:
        entity = _entity(status=ObjectFeatureStatus.DISABLED)
        use_case = AssertObjectFeatureEnabledUseCase(_RepositoryStub(config=entity))

        with self.assertRaises(ObjectFeatureNotEnabledError):
            await use_case(
                tenant_id=entity.tenant_id,
                object_id=entity.object_id,
                feature_code="CONTACT_POINT",
            )

    async def test_disable_not_found(self) -> None:
        object_id = RuntimeObjectIdVO.from_value(uuid4())
        use_case = DisableObjectFeatureUseCase(
            repository=_RepositoryStub(config=None),
            clock=_ClockStub(datetime.now(UTC)),
        )

        with self.assertRaises(ObjectFeatureConfigNotFoundError):
            await use_case(
                DisableObjectFeatureCommand(
                    tenant_id=EntityIdVO.from_value(uuid4()),
                    object_id=object_id,
                    feature_code=FeatureCodeVO("CONTACT_POINT"),
                )
            )


__all__ = ["SchemaRegistryObjectFeatureUseCaseTests"]
