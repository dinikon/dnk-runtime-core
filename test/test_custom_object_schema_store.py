from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.custom_object.application import (
    AddCustomFieldCommand,
    CreateCustomObjectCommand,
    CustomFieldInput,
)
from src.modules.custom_object.domain import CustomObjectValidationError
from src.modules.custom_object.infrastructure import SchemaRegistryCustomObjectStore
from src.modules.schema_registry.application.migration.operations import (
    AddColumnOperation,
    CreateIndexOperation,
    CreateTableOperation,
)
from src.modules.schema_registry.application.migration.postgres_field_canonicalizer import (
    PostgresFieldCanonicalizer,
)
from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.schema_registry.domain.datasource.value_object import DataSourceIdVO
from src.modules.schema_registry.domain.datasource.value_object.schema_name import (
    SchemaNameVO,
)
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.field.value_object import RuntimeFieldIdVO
from src.modules.schema_registry.domain.object.entity import ObjectEntity
from src.modules.schema_registry.domain.object.value_object import RuntimeObjectIdVO
from src.modules.schema_registry.domain.object.value_object.object_kind import (
    ObjectKind,
)
from src.modules.schema_registry.domain.object.value_object.object_label import (
    ObjectLabelVO,
)
from src.modules.schema_registry.domain.object.value_object.object_name import (
    ObjectNameVO,
)
from src.modules.shared import TenantIdVO


class _ClockStub:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class _DataSourceServiceStub:
    def __init__(self, datasource: DataSourceEntity) -> None:
        self.datasource = datasource

    async def get_required_by_tenant(self, *, tenant_id):
        return self.datasource


class _ObjectRepositoryStub:
    def __init__(self, objects: list[ObjectEntity] | None = None) -> None:
        self.objects = list(objects or [])
        self.saved: ObjectEntity | None = None
        self.reconciled: list[ObjectEntity] | None = None

    async def get_by_tenant_and_singular_name(self, *, tenant_id, singular_name):
        for item in self.objects:
            if (
                item.tenant_id == tenant_id
                and item.object_name.singular == singular_name
            ):
                return item
        return None

    async def get_by_tenant_and_plural_name(self, *, tenant_id, plural_name):
        for item in self.objects:
            if item.tenant_id == tenant_id and item.object_name.plural == plural_name:
                return item
        return None

    async def get_by_id(self, *, object_id):
        for item in self.objects:
            if item.id == object_id:
                return item
        return None

    async def save(self, object_entity):
        self.saved = object_entity
        self.objects = [item for item in self.objects if item.id != object_entity.id]
        self.objects.append(object_entity)

    async def list_by_tenant_id(self, *, tenant_id):
        return [item for item in self.objects if item.tenant_id == tenant_id]

    async def replace_all_for_tenant(self, *, tenant_id, objects):
        self.objects = list(objects)

    async def reconcile_for_tenant(self, *, tenant_id, objects):
        self.reconciled = list(objects)
        self.objects = list(objects)


class _TenantSchemaExecutorSpy:
    def __init__(self) -> None:
        self.operations = []

    async def execute(self, *, plan):
        self.operations.extend(plan.operations)


class CustomObjectSchemaStoreTests(unittest.IsolatedAsyncioTestCase):
    def _datasource(self, tenant_id: TenantIdVO, now: datetime) -> DataSourceEntity:
        return DataSourceEntity.create(
            id_=DataSourceIdVO.from_value(uuid4()),
            now=now,
            tenant_id=tenant_id,
            schema_name=SchemaNameVO("dnk_test"),
        )

    def _store(
        self,
        *,
        repository: _ObjectRepositoryStub,
        executor: _TenantSchemaExecutorSpy,
        tenant_id: TenantIdVO,
        now: datetime,
        object_ids: list[RuntimeObjectIdVO] | None = None,
        field_ids: list[RuntimeFieldIdVO] | None = None,
    ) -> SchemaRegistryCustomObjectStore:
        object_id_iter = iter(object_ids or [RuntimeObjectIdVO.from_value(uuid4())])
        field_id_iter = iter(
            field_ids or [RuntimeFieldIdVO.from_value(uuid4()) for _item in range(8)]
        )
        return SchemaRegistryCustomObjectStore(
            object_repository=repository,
            data_source_service=_DataSourceServiceStub(
                self._datasource(tenant_id, now)
            ),
            tenant_schema_executor=executor,
            postgres_field_canonicalizer=PostgresFieldCanonicalizer(),
            field_type_catalog=FieldTypeCatalog(),
            clock=_ClockStub(now),
            object_id_provider=lambda: next(object_id_iter),
            field_id_provider=lambda: next(field_id_iter),
        )

    async def test_create_object_adds_system_fields_and_targeted_ddl(self) -> None:
        tenant_id = TenantIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        repository = _ObjectRepositoryStub()
        executor = _TenantSchemaExecutorSpy()
        store = self._store(
            repository=repository,
            executor=executor,
            tenant_id=tenant_id,
            now=now,
        )

        result = await store.create_object(
            CreateCustomObjectCommand(
                tenant_id=tenant_id,
                singular_name="deal",
                plural_name="deals",
                singular_label="Deal",
                plural_label="Deals",
                description="Sales deals.",
                fields=(
                    CustomFieldInput(
                        field_name="status",
                        type="select",
                        label="Status",
                        is_nullable=False,
                        default_value="'new'",
                        options={"new": "New", "won": "Won"},
                    ),
                ),
            )
        )

        self.assertEqual(result.kind, "custom")
        self.assertEqual(
            [field.field_name for field in result.fields[:3]],
            [
                "id",
                "created_at",
                "updated_at",
            ],
        )
        self.assertEqual(result.fields[3].field_name, "status")
        self.assertEqual(result.fields[3].kind, "custom")
        self.assertIs(repository.saved, repository.objects[0])
        self.assertIsInstance(executor.operations[0], CreateTableOperation)
        self.assertEqual(
            [
                operation.column_name
                for operation in executor.operations
                if isinstance(operation, AddColumnOperation)
            ],
            ["id", "created_at", "updated_at", "status"],
        )
        self.assertTrue(
            any(
                isinstance(operation, CreateIndexOperation)
                for operation in executor.operations
            )
        )

    async def test_add_field_rejects_required_column_without_default(self) -> None:
        tenant_id = TenantIdVO.from_value(uuid4())
        datasource_id = DataSourceIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        object_entity = ObjectEntity.create(
            id_=RuntimeObjectIdVO.from_value(uuid4()),
            tenant_id=tenant_id,
            data_source_id=datasource_id,
            now=now,
            object_name=ObjectNameVO(singular="deal", plural="deals"),
            object_label=ObjectLabelVO(singular="Deal", plural="Deals"),
            description="Sales deals.",
            kind=ObjectKind.CUSTOM,
        )
        repository = _ObjectRepositoryStub([object_entity])
        executor = _TenantSchemaExecutorSpy()
        store = self._store(
            repository=repository,
            executor=executor,
            tenant_id=tenant_id,
            now=now,
        )

        with self.assertRaises(CustomObjectValidationError):
            await store.add_field(
                AddCustomFieldCommand(
                    tenant_id=tenant_id,
                    object_id=object_entity.id,
                    field=CustomFieldInput(
                        field_name="amount",
                        type="decimal",
                        label="Amount",
                        is_nullable=False,
                    ),
                )
            )

        self.assertEqual(executor.operations, [])


__all__ = ["CustomObjectSchemaStoreTests"]
