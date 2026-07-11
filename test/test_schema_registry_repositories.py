from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.schema_registry.domain.datasource.value_object import DataSourceIdVO
from src.modules.schema_registry.domain.datasource.value_object.schema_name import (
    SchemaNameVO,
)
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.field.value_object import RuntimeFieldIdVO
from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
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
from src.modules.schema_registry.domain.relation.entity import RelationEntity
from src.modules.schema_registry.domain.relation.value_object import RuntimeRelationIdVO
from src.modules.schema_registry.domain.seed.relation_type import RelationTypeEnum
from src.modules.schema_registry.infrastructure.persistence.data_source import (
    DataSourceORM,
)
from src.modules.schema_registry.infrastructure.persistence.field import FieldORM
from src.modules.schema_registry.infrastructure.persistence.object import ObjectORM
from src.modules.schema_registry.infrastructure.persistence.relation import RelationORM
from src.modules.schema_registry.infrastructure.repository.data_source_repository import (
    SqlAlchemyDataSourceRepository,
)
from src.modules.schema_registry.infrastructure.repository.object_repository import (
    SqlAlchemyObjectRepository,
)
from src.modules.schema_registry.infrastructure.repository.relation_repository import (
    SqlAlchemyRelationRepository,
)
from src.modules.shared import EntityIdVO


class ScalarsResult:
    def __init__(self, values: list[object]) -> None:
        self._values = values

    def all(self) -> list[object]:
        return list(self._values)


class SchemaRegistryRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_object_repository_preserves_tenant_and_data_source_ids(self) -> None:
        tenant_id = uuid4()
        datasource_id = uuid4()
        object_id = uuid4()
        field_id = uuid4()
        now = datetime.now(UTC)

        object_model = ObjectORM(
            id=object_id,
            created_at=now,
            updated_at=now,
            tenant_id=tenant_id,
            data_source_id=datasource_id,
            kind="standard",
            singular_name="contact",
            plural_name="contacts",
            singular_label="Contact",
            plural_label="Contacts",
            description="Tenant contacts.",
        )
        field_model = FieldORM(
            id=field_id,
            created_at=now,
            updated_at=now,
            object_id=object_id,
            kind="system",
            field_name="last_name",
            field_type_code="text",
            label="Last Name",
            description="Contact last name.",
            is_nullable=False,
            default_value=None,
            options={},
            settings={},
        )

        class SessionStub:
            def __init__(self) -> None:
                self.scalars_call_count = 0

            async def scalars(self, *_args, **_kwargs):
                self.scalars_call_count += 1
                if self.scalars_call_count == 1:
                    return ScalarsResult([object_model])
                if self.scalars_call_count == 2:
                    return ScalarsResult([field_model])
                return ScalarsResult([])

        repository = SqlAlchemyObjectRepository(SessionStub())  # type: ignore[arg-type]
        objects = await repository.list_by_tenant_id(
            tenant_id=EntityIdVO.from_value(tenant_id)
        )

        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0].tenant_id, EntityIdVO.from_value(tenant_id))
        self.assertEqual(
            objects[0].data_source_id, DataSourceIdVO.from_value(datasource_id)
        )
        self.assertEqual(objects[0].kind, ObjectKind.STANDARD)
        self.assertEqual(objects[0].fields[0].kind, FieldKind.SYSTEM)
        self.assertEqual(objects[0].fields[0].field_name.value, "last_name")

    async def test_data_source_repository_add_maps_entity_to_orm_model(self) -> None:
        tenant_id = uuid4()
        datasource_id = uuid4()
        now = datetime.now(UTC)

        datasource = DataSourceEntity.create(
            id_=DataSourceIdVO.from_value(datasource_id),
            now=now,
            tenant_id=EntityIdVO.from_value(tenant_id),
            schema_name=SchemaNameVO("dnk_test"),
        )

        class SessionSpy:
            def __init__(self) -> None:
                self.added_models: list[object] = []
                self.flush_count = 0

            def add(self, model) -> None:
                self.added_models.append(model)

            async def flush(self) -> None:
                self.flush_count += 1

        session = SessionSpy()
        repository = SqlAlchemyDataSourceRepository(session)  # type: ignore[arg-type]

        await repository.add(datasource)

        self.assertEqual(session.flush_count, 1)
        self.assertEqual(len(session.added_models), 1)
        model = session.added_models[0]
        self.assertIsInstance(model, DataSourceORM)
        assert isinstance(model, DataSourceORM)
        self.assertEqual(model.id, datasource.id.uuid)
        self.assertEqual(model.tenant_id, datasource.tenant_id.uuid)
        self.assertEqual(model.data_source_type, datasource.data_source_type.value)
        self.assertEqual(model.schema_name, datasource.schema_name.value)
        self.assertEqual(model.connection_dsn, None)

    async def test_replace_all_flushes_objects_before_fields(self) -> None:
        tenant_id = uuid4()
        datasource_id = DataSourceIdVO.from_value(uuid4())
        now = datetime.now(UTC)

        object_entity = ObjectEntity.create(
            id_=RuntimeObjectIdVO.from_value(uuid4()),
            tenant_id=EntityIdVO.from_value(tenant_id),
            data_source_id=datasource_id,
            now=now,
            object_name=ObjectNameVO(singular="contact", plural="contacts"),
            object_label=ObjectLabelVO(singular="Contact", plural="Contacts"),
            description="Tenant contacts.",
            kind=ObjectKind.CUSTOM,
        )
        object_entity.add_field(
            field_id=RuntimeFieldIdVO.from_value(uuid4()),
            now=now,
            field_name="last_name",
            field_type=FieldTypeCatalog().from_seed_type("text"),
            label="Last Name",
            description="Contact last name.",
            is_nullable=False,
            kind=FieldKind.SYSTEM,
        )

        class SessionSpy:
            def __init__(self) -> None:
                self.flush_snapshots: list[list[str]] = []
                self.added_types: list[str] = []
                self.added_models: list[object] = []

            async def scalars(self, *_args, **_kwargs):
                return ScalarsResult([])

            async def execute(self, *_args, **_kwargs) -> None:
                return None

            def add(self, model) -> None:
                self.added_models.append(model)
                self.added_types.append(type(model).__name__)

            async def flush(self) -> None:
                self.flush_snapshots.append(list(self.added_types))

        session = SessionSpy()
        repository = SqlAlchemyObjectRepository(session)  # type: ignore[arg-type]

        await repository.replace_all_for_tenant(
            tenant_id=EntityIdVO.from_value(tenant_id),
            objects=[object_entity],
        )

        self.assertEqual(
            session.flush_snapshots,
            [[], ["ObjectORM"], ["ObjectORM", "FieldORM"]],
        )
        object_model = next(
            model for model in session.added_models if isinstance(model, ObjectORM)
        )
        field_model = next(
            model for model in session.added_models if isinstance(model, FieldORM)
        )
        self.assertEqual(object_model.kind, "custom")
        self.assertEqual(field_model.kind, "system")

    async def test_reconcile_preserves_existing_field_identity(self) -> None:
        tenant_id = uuid4()
        now = datetime.now(UTC)
        object_id = uuid4()
        field_id = uuid4()
        data_source_id = uuid4()

        object_entity = ObjectEntity.create(
            id_=RuntimeObjectIdVO.from_value(object_id),
            tenant_id=EntityIdVO.from_value(tenant_id),
            data_source_id=DataSourceIdVO.from_value(data_source_id),
            now=now,
            object_name=ObjectNameVO(singular="contact", plural="contacts"),
            object_label=ObjectLabelVO(singular="Contact", plural="Contacts"),
            description="Tenant contacts.",
        )
        object_entity.add_field(
            field_id=RuntimeFieldIdVO.from_value(field_id),
            now=now,
            field_name="last_name",
            field_type=FieldTypeCatalog().from_seed_type("text"),
            label="Surname",
            description="Contact last name.",
            is_nullable=False,
        )

        object_model = ObjectORM(
            id=object_id,
            created_at=now,
            updated_at=now,
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            kind="standard",
            singular_name="contact",
            plural_name="contacts",
            singular_label="Contact",
            plural_label="Contacts",
            description="Tenant contacts.",
        )
        field_model = FieldORM(
            id=field_id,
            created_at=now,
            updated_at=now,
            object_id=object_id,
            kind="standard",
            field_name="last_name",
            field_type_code="text",
            label="Last Name",
            description="Contact last name.",
            is_nullable=False,
            default_value=None,
            options={},
            settings={},
        )

        class SessionSpy:
            def __init__(self) -> None:
                self.scalars_calls = 0
                self.added_models: list[object] = []

            async def scalars(self, *_args, **_kwargs):
                self.scalars_calls += 1
                if self.scalars_calls == 1:
                    return ScalarsResult([object_id])
                if self.scalars_calls == 2:
                    return ScalarsResult([field_id])
                return ScalarsResult([])

            async def execute(self, *_args, **_kwargs) -> None:
                return None

            async def get(self, model_cls, model_id):
                if model_cls is ObjectORM and model_id == object_id:
                    return object_model
                if model_cls is FieldORM and model_id == field_id:
                    return field_model
                return None

            def add(self, model) -> None:
                self.added_models.append(model)

            async def flush(self) -> None:
                return None

        session = SessionSpy()
        object_repository = SqlAlchemyObjectRepository(session)  # type: ignore[arg-type]

        await object_repository.reconcile_for_tenant(
            tenant_id=EntityIdVO.from_value(tenant_id),
            objects=[object_entity],
        )

        self.assertEqual(field_model.id, field_id)
        self.assertEqual(field_model.label, "Surname")
        self.assertEqual(field_model.kind, "standard")
        self.assertFalse(
            any(isinstance(model, FieldORM) for model in session.added_models)
        )

    async def test_reconcile_deletes_fields_before_retired_object(self) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        retired_object_id = uuid4()

        class SessionSpy:
            def __init__(self) -> None:
                self.deleted_tables: list[str] = []

            async def scalars(self, *_args, **_kwargs):
                return ScalarsResult([retired_object_id])

            async def execute(self, statement) -> None:
                self.deleted_tables.append(statement.table.name)

            async def flush(self) -> None:
                return None

        session = SessionSpy()
        repository = SqlAlchemyObjectRepository(session)  # type: ignore[arg-type]

        await repository.reconcile_for_tenant(
            tenant_id=tenant_id,
            objects=[],
        )

        self.assertEqual(
            session.deleted_tables,
            ["fields", "objects"],
        )

    async def test_relation_repository_replace_all_maps_entity_to_orm_model(
        self,
    ) -> None:
        tenant_id = EntityIdVO.from_value(uuid4())
        datasource_id = DataSourceIdVO.from_value(uuid4())
        now = datetime.now(UTC)
        source_object_id = RuntimeObjectIdVO.from_value(uuid4())
        target_object_id = RuntimeObjectIdVO.from_value(uuid4())
        fk_field_id = RuntimeFieldIdVO.from_value(uuid4())
        referenced_field_id = RuntimeFieldIdVO.from_value(uuid4())
        relation = RelationEntity.create(
            id_=RuntimeRelationIdVO.from_value(uuid4()),
            now=now,
            tenant_id=tenant_id,
            data_source_id=datasource_id,
            name="contacts_company",
            relation_type=RelationTypeEnum.MANY_TO_ONE,
            source_object_id=source_object_id,
            target_object_id=target_object_id,
            owning_object_id=source_object_id,
            fk_field_id=fk_field_id,
            referenced_object_id=target_object_id,
            referenced_field_id=referenced_field_id,
            source_relation_name="company",
            target_relation_name="contacts",
            relation_table_name=None,
            source_join_column_name=None,
            target_join_column_name=None,
            on_delete="restrict",
            is_required=False,
            is_unique=False,
            kind="standard",
        )

        class SessionSpy:
            def __init__(self) -> None:
                self.added_models: list[object] = []
                self.execute_count = 0
                self.flush_count = 0

            async def execute(self, *_args, **_kwargs) -> None:
                self.execute_count += 1
                return None

            def add(self, model) -> None:
                self.added_models.append(model)

            async def flush(self) -> None:
                self.flush_count += 1

        session = SessionSpy()
        repository = SqlAlchemyRelationRepository(session)  # type: ignore[arg-type]

        await repository.replace_all_for_tenant(
            tenant_id=tenant_id,
            relations=[relation],
        )

        self.assertEqual(session.execute_count, 1)
        self.assertEqual(session.flush_count, 2)
        self.assertEqual(len(session.added_models), 1)
        model = session.added_models[0]
        self.assertIsInstance(model, RelationORM)
        assert isinstance(model, RelationORM)
        self.assertEqual(model.name, "contacts_company")
        self.assertEqual(model.relation_type, "many_to_one")
        self.assertEqual(model.fk_field_id, fk_field_id.uuid)
