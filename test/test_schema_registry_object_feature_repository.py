from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object_feature.entity import (
    ObjectFeatureConfigEntity,
)
from src.modules.schema_registry.domain.object_feature.value_object import (
    FeatureCodeVO,
    ObjectFeatureConfigIdVO,
    ObjectFeatureKind,
    ObjectFeatureStatus,
)
from src.modules.schema_registry.infrastructure.persistence.object_feature_config import (
    ObjectFeatureConfigORM,
)
from src.modules.schema_registry.infrastructure.repository.object_feature_config_repository import (
    SqlAlchemyObjectFeatureConfigRepository,
)
from src.modules.shared import EntityIdVO


class _ScalarsResult:
    def __init__(self, values: list[ObjectFeatureConfigORM]) -> None:
        self._values = values

    def all(self) -> list[ObjectFeatureConfigORM]:
        return list(self._values)


class _SessionSpy:
    def __init__(
        self,
        *,
        model: ObjectFeatureConfigORM | None = None,
        models: list[ObjectFeatureConfigORM] | None = None,
    ) -> None:
        self.model = model
        self.models = models or []
        self.added: list[ObjectFeatureConfigORM] = []
        self.flush_count = 0
        self.get_primary_key = None
        self.scalar_called = False
        self.scalars_called = False

    async def scalar(self, *_args, **_kwargs) -> ObjectFeatureConfigORM | None:
        self.scalar_called = True
        return self.model

    async def get(self, _model_type, primary_key):
        self.get_primary_key = primary_key
        return self.model

    def add(self, model: ObjectFeatureConfigORM) -> None:
        self.added.append(model)

    async def flush(self) -> None:
        self.flush_count += 1

    async def scalars(self, *_args, **_kwargs) -> _ScalarsResult:
        self.scalars_called = True
        return _ScalarsResult(self.models)


def _entity(
    *,
    now: datetime | None = None,
    config: dict[str, object] | None = None,
) -> ObjectFeatureConfigEntity:
    timestamp = now or datetime.now(UTC)
    return ObjectFeatureConfigEntity.create(
        id_=ObjectFeatureConfigIdVO.from_value(uuid4()),
        now=timestamp,
        tenant_id=EntityIdVO.from_value(uuid4()),
        object_id=RuntimeObjectIdVO.from_value(uuid4()),
        feature_code=FeatureCodeVO("CONTACT_POINT"),
        kind=ObjectFeatureKind.CUSTOM,
        status=ObjectFeatureStatus.ENABLED,
        config=config or {"schema": "contact"},
    )


def _model(
    *,
    entity: ObjectFeatureConfigEntity | None = None,
) -> ObjectFeatureConfigORM:
    source = entity or _entity()
    return ObjectFeatureConfigORM(
        object_feature_config_id=source.id.uuid,
        created_at=source.created_at,
        updated_at=source.updated_at,
        tenant_id=source.tenant_id.uuid,
        object_id=source.object_id.uuid,
        feature_code=source.feature_code.value,
        kind=source.kind.value,
        status=source.status.value,
        config=dict(source.config),
        is_locked=source.is_locked,
        locked_reason=source.locked_reason,
    )


class SchemaRegistryObjectFeatureRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_save_insert(self) -> None:
        entity = _entity()
        session = _SessionSpy(model=None)
        repository = SqlAlchemyObjectFeatureConfigRepository(session)  # type: ignore[arg-type]

        await repository.save(entity)

        self.assertEqual(session.flush_count, 1)
        self.assertEqual(len(session.added), 1)
        self.assertEqual(session.added[0].feature_code, "CONTACT_POINT")

    async def test_save_update(self) -> None:
        entity = _entity(config={"version": 1})
        model = _model(entity=entity)
        entity.update_config(now=entity.updated_at, config={"version": 2})
        session = _SessionSpy(model=model)
        repository = SqlAlchemyObjectFeatureConfigRepository(session)  # type: ignore[arg-type]

        await repository.save(entity)

        self.assertEqual(session.flush_count, 1)
        self.assertEqual(model.config, {"version": 2})
        self.assertEqual(model.status, "enabled")

    async def test_get_by_tenant_object_feature(self) -> None:
        entity = _entity()
        session = _SessionSpy(model=_model(entity=entity))
        repository = SqlAlchemyObjectFeatureConfigRepository(session)  # type: ignore[arg-type]

        result = await repository.get(
            tenant_id=entity.tenant_id,
            object_id=entity.object_id,
            feature_code=entity.feature_code,
        )

        self.assertTrue(session.scalar_called)
        assert result is not None
        self.assertEqual(result.id, entity.id)
        self.assertEqual(result.feature_code.value, "CONTACT_POINT")

    async def test_list_by_object(self) -> None:
        first = _entity()
        second = _entity()
        session = _SessionSpy(models=[_model(entity=first), _model(entity=second)])
        repository = SqlAlchemyObjectFeatureConfigRepository(session)  # type: ignore[arg-type]

        result = await repository.list_by_object(
            tenant_id=first.tenant_id,
            object_id=first.object_id,
        )

        self.assertTrue(session.scalars_called)
        self.assertEqual([item.id for item in result], [first.id, second.id])

    def test_to_model(self) -> None:
        entity = _entity(config={"fields": ["email"]})

        model = SqlAlchemyObjectFeatureConfigRepository._to_model(entity)

        self.assertEqual(model.object_feature_config_id, entity.id.uuid)
        self.assertEqual(model.tenant_id, entity.tenant_id.uuid)
        self.assertEqual(model.object_id, entity.object_id.uuid)
        self.assertEqual(model.feature_code, "CONTACT_POINT")
        self.assertEqual(model.config, {"fields": ["email"]})

    def test_update_model(self) -> None:
        entity = _entity(config={"old": True})
        model = _model(entity=entity)
        entity.disable(now=entity.updated_at)
        entity.update_config(now=entity.updated_at, config={"new": True})

        SqlAlchemyObjectFeatureConfigRepository._update_model(model, entity)

        self.assertEqual(model.status, "disabled")
        self.assertEqual(model.config, {"new": True})

    def test_map_model(self) -> None:
        entity = _entity(config={"x": 1})
        model = _model(entity=entity)

        result = SqlAlchemyObjectFeatureConfigRepository._map_model(model)

        self.assertEqual(result.id, entity.id)
        self.assertEqual(result.tenant_id, entity.tenant_id)
        self.assertEqual(result.object_id, entity.object_id)
        self.assertEqual(result.feature_code, FeatureCodeVO("CONTACT_POINT"))
        self.assertEqual(result.config, {"x": 1})


__all__ = ["SchemaRegistryObjectFeatureRepositoryTests"]
