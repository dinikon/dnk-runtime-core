from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.schema_registry.application.config.field.command import (
    AddCustomFieldCommand,
    CustomFieldInput,
    DeleteCustomFieldCommand,
)
from src.modules.schema_registry.application.config.object.command import (
    CreateCustomObjectCommand,
    DeleteCustomObjectCommand,
)
from src.modules.schema_registry.application.config.object.query import (
    CustomObjectByIdQuery,
    ListCustomObjectsQuery,
)
from src.modules.schema_registry.application.migration.operations import (
    AddColumnOperation,
    CreateIndexOperation,
    DropColumnOperation,
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
from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.error import (
    InvalidFieldOperationError,
    InvalidObjectOperationError,
    ObjectNameAlreadyExistsError,
    UnsupportedSchemaChangeError,
)
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
from src.modules.schema_registry.infrastructure.config import SchemaConfigRepository
from src.modules.shared import EntityIdVO


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


class SchemaConfigRepositoryTests(unittest.IsolatedAsyncioTestCase):

    def _datasource(self, tenant_id: EntityIdVO, now: datetime) -> DataSourceEntity:
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
        tenant_id: EntityIdVO,
        now: datetime,
        object_ids: list[RuntimeObjectIdVO] | None = None,
        field_ids: list[RuntimeFieldIdVO] | None = None,
    ) -> SchemaConfigRepository:
        object_id_iter = iter(object_ids or [RuntimeObjectIdVO.from_value(uuid4())])
        field_id_iter = iter(
            field_ids or [RuntimeFieldIdVO.from_value(uuid4()) for _item in range(8)]
        )
        return SchemaConfigRepository(
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

    def _object(
        self,
        *,
        tenant_id: EntityIdVO,
        datasource_id: DataSourceIdVO,
        now: datetime,
        singular: str = "deal",
        plural: str = "deals",
        kind: ObjectKind = ObjectKind.CUSTOM,
    ) -> ObjectEntity:
        return ObjectEntity.create(
            id_=RuntimeObjectIdVO.from_value(uuid4()),
            tenant_id=tenant_id,
            data_source_id=datasource_id,
            now=now,
            object_name=ObjectNameVO(singular=singular, plural=plural),
            object_label=ObjectLabelVO(
                singular=singular.title(), plural=plural.title()
            ),
            description=f"{plural.title()}.",
            kind=kind,
        )

    def _add_field(
        self,
        object_entity: ObjectEntity,
        *,
        now: datetime,
        field_name: str,
        kind: FieldKind = FieldKind.CUSTOM,
        is_nullable: bool = True,
    ) -> RuntimeFieldIdVO:
        field_id = RuntimeFieldIdVO.from_value(uuid4())
        object_entity.add_field(
            field_id=field_id,
            now=now,
            field_name=field_name,
            field_type=FieldTypeCatalog().from_seed_type("text"),
            label=field_name.title(),
            description="",
            is_nullable=is_nullable,
            kind=kind,
        )
        return field_id

    async def test_create_object_adds_system_fields_and_targeted_ddl(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
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
        self.assertEqual(result.singular_name, "c_deal")
        self.assertEqual(result.plural_name, "c_deals")
        self.assertEqual([field.field_name for field in result.fields], ["status"])
        self.assertEqual(result.fields[0].kind, "custom")
        self.assertEqual(repository.saved.object_name.singular, "c_deal")
        self.assertEqual(repository.saved.object_name.plural, "c_deals")
        self.assertEqual(
            [field.field_name.value for field in repository.saved.fields[:3]],
            ["id", "created_at", "updated_at"],
        )
        self.assertIs(repository.saved, repository.objects[0])
        self.assertIsInstance(executor.operations[0], CreateTableOperation)
        self.assertEqual(executor.operations[0].table_name, "c_deals")
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

    async def test_create_object_keeps_existing_custom_prefix(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
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
                singular_name="c_deal",
                plural_name="c_deals",
                singular_label="Deal",
                plural_label="Deals",
                description="Sales deals.",
            )
        )

        self.assertEqual(result.singular_name, "c_deal")
        self.assertEqual(result.plural_name, "c_deals")
        self.assertEqual(executor.operations[0].table_name, "c_deals")

    async def test_create_object_checks_duplicates_after_custom_prefix(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        repository = _ObjectRepositoryStub()
        store = self._store(
            repository=repository,
            executor=_TenantSchemaExecutorSpy(),
            tenant_id=tenant_id,
            now=now,
        )

        await store.create_object(
            CreateCustomObjectCommand(
                tenant_id=tenant_id,
                singular_name="deal",
                plural_name="deals",
                singular_label="Deal",
                plural_label="Deals",
                description="Sales deals.",
            )
        )

        with self.assertRaises(ObjectNameAlreadyExistsError):
            await store.create_object(
                CreateCustomObjectCommand(
                    tenant_id=tenant_id,
                    singular_name="c_deal",
                    plural_name="c_deals",
                    singular_label="Deal",
                    plural_label="Deals",
                    description="Sales deals.",
                )
            )

    async def test_create_custom_object_does_not_conflict_with_standard_name(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        datasource_id = DataSourceIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        standard = self._object(
            tenant_id=tenant_id,
            datasource_id=datasource_id,
            now=now,
            singular="contact",
            plural="contacts",
            kind=ObjectKind.STANDARD,
        )
        repository = _ObjectRepositoryStub([standard])
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
                singular_name="contact",
                plural_name="contacts",
                singular_label="Contact",
                plural_label="Contacts",
                description="Custom contacts.",
            )
        )

        self.assertEqual(result.singular_name, "c_contact")
        self.assertEqual(result.plural_name, "c_contacts")
        self.assertEqual(executor.operations[0].table_name, "c_contacts")
        self.assertEqual(
            [item.object_name.plural for item in repository.objects],
            ["contacts", "c_contacts"],
        )

    async def test_add_field_rejects_required_column_without_default(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        datasource_id = DataSourceIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        object_entity = self._object(
            tenant_id=tenant_id,
            datasource_id=datasource_id,
            now=now,
        )
        repository = _ObjectRepositoryStub([object_entity])
        executor = _TenantSchemaExecutorSpy()
        store = self._store(
            repository=repository,
            executor=executor,
            tenant_id=tenant_id,
            now=now,
        )

        with self.assertRaises(UnsupportedSchemaChangeError):
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

    async def test_list_and_schema_include_all_object_kinds_and_hide_system_fields(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        datasource_id = DataSourceIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        standard = self._object(
            tenant_id=tenant_id,
            datasource_id=datasource_id,
            now=now,
            singular="contact",
            plural="contacts",
            kind=ObjectKind.STANDARD,
        )
        self._add_field(standard, now=now, field_name="id", kind=FieldKind.SYSTEM)
        self._add_field(standard, now=now, field_name="email", kind=FieldKind.STANDARD)
        system = self._object(
            tenant_id=tenant_id,
            datasource_id=datasource_id,
            now=now,
            singular="audit_event",
            plural="audit_events",
            kind=ObjectKind.SYSTEM,
        )
        custom = self._object(
            tenant_id=tenant_id,
            datasource_id=datasource_id,
            now=now,
            singular="deal",
            plural="deals",
            kind=ObjectKind.CUSTOM,
        )
        repository = _ObjectRepositoryStub([standard, system, custom])
        store = self._store(
            repository=repository,
            executor=_TenantSchemaExecutorSpy(),
            tenant_id=tenant_id,
            now=now,
        )

        result = await store.list_objects(ListCustomObjectsQuery(tenant_id=tenant_id))
        described = await store.describe_object(
            CustomObjectByIdQuery(tenant_id=tenant_id, object_id=standard.id)
        )

        self.assertEqual(
            [item.kind for item in result], ["standard", "system", "custom"]
        )
        self.assertEqual([field.field_name for field in described.fields], ["email"])

    async def test_standard_object_accepts_custom_field(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        datasource_id = DataSourceIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        object_entity = self._object(
            tenant_id=tenant_id,
            datasource_id=datasource_id,
            now=now,
            kind=ObjectKind.STANDARD,
        )
        repository = _ObjectRepositoryStub([object_entity])
        executor = _TenantSchemaExecutorSpy()
        store = self._store(
            repository=repository,
            executor=executor,
            tenant_id=tenant_id,
            now=now,
        )

        result = await store.add_field(
            AddCustomFieldCommand(
                tenant_id=tenant_id,
                object_id=object_entity.id,
                field=CustomFieldInput(
                    field_name="tier",
                    type="text",
                    label="Tier",
                    is_nullable=True,
                ),
            )
        )

        self.assertEqual(result.fields[-1].field_name, "tier")
        self.assertIsInstance(executor.operations[-1], AddColumnOperation)
        self.assertIs(repository.saved, object_entity)

    async def test_system_and_view_objects_reject_field_mutation(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        datasource_id = DataSourceIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        repository = _ObjectRepositoryStub(
            [
                self._object(
                    tenant_id=tenant_id,
                    datasource_id=datasource_id,
                    now=now,
                    singular="audit_event",
                    plural="audit_events",
                    kind=ObjectKind.SYSTEM,
                ),
                self._object(
                    tenant_id=tenant_id,
                    datasource_id=datasource_id,
                    now=now,
                    singular="report",
                    plural="reports",
                    kind=ObjectKind.VIEW,
                ),
            ]
        )
        store = self._store(
            repository=repository,
            executor=_TenantSchemaExecutorSpy(),
            tenant_id=tenant_id,
            now=now,
        )

        for object_entity in repository.objects:
            with self.assertRaises(InvalidObjectOperationError):
                await store.add_field(
                    AddCustomFieldCommand(
                        tenant_id=tenant_id,
                        object_id=object_entity.id,
                        field=CustomFieldInput(
                            field_name="note",
                            type="text",
                            label="Note",
                        ),
                    )
                )

    async def test_only_custom_objects_can_be_deleted(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        datasource_id = DataSourceIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        standard = self._object(
            tenant_id=tenant_id,
            datasource_id=datasource_id,
            now=now,
            kind=ObjectKind.STANDARD,
        )
        custom = self._object(
            tenant_id=tenant_id,
            datasource_id=datasource_id,
            now=now,
            singular="note",
            plural="notes",
            kind=ObjectKind.CUSTOM,
        )
        repository = _ObjectRepositoryStub([standard, custom])
        executor = _TenantSchemaExecutorSpy()
        store = self._store(
            repository=repository,
            executor=executor,
            tenant_id=tenant_id,
            now=now,
        )

        with self.assertRaises(InvalidObjectOperationError):
            await store.delete_object(
                DeleteCustomObjectCommand(tenant_id=tenant_id, object_id=standard.id)
            )

        await store.delete_object(
            DeleteCustomObjectCommand(tenant_id=tenant_id, object_id=custom.id)
        )

        self.assertEqual(repository.objects, [standard])

    async def test_only_custom_fields_can_be_deleted(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        datasource_id = DataSourceIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        object_entity = self._object(
            tenant_id=tenant_id,
            datasource_id=datasource_id,
            now=now,
            kind=ObjectKind.STANDARD,
        )
        standard_field_id = self._add_field(
            object_entity,
            now=now,
            field_name="email",
            kind=FieldKind.STANDARD,
        )
        custom_field_id = self._add_field(
            object_entity,
            now=now,
            field_name="tier",
            kind=FieldKind.CUSTOM,
        )
        repository = _ObjectRepositoryStub([object_entity])
        executor = _TenantSchemaExecutorSpy()
        store = self._store(
            repository=repository,
            executor=executor,
            tenant_id=tenant_id,
            now=now,
        )

        with self.assertRaises(InvalidFieldOperationError):
            await store.delete_field(
                DeleteCustomFieldCommand(
                    tenant_id=tenant_id,
                    object_id=object_entity.id,
                    field_id=standard_field_id,
                )
            )

        result = await store.delete_field(
            DeleteCustomFieldCommand(
                tenant_id=tenant_id,
                object_id=object_entity.id,
                field_id=custom_field_id,
            )
        )

        self.assertEqual([field.field_name for field in result.fields], ["email"])
        self.assertIsInstance(executor.operations[-1], DropColumnOperation)


__all__ = ["SchemaConfigRepositoryTests"]
