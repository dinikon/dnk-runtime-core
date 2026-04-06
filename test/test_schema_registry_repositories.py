from __future__ import annotations

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.modules.schema_registry.domain.datasource.entity import DataSourceEntity
from src.modules.schema_registry.domain.datasource.value_object.schema_name import (
    SchemaNameVO,
)
from src.modules.schema_registry.domain.field.service import FieldTypeService
from src.modules.schema_registry.domain.object.entity import ObjectEntity
from src.modules.schema_registry.domain.object.value_object.object_label import (
    ObjectLabelVO,
)
from src.modules.schema_registry.domain.object.value_object.object_name import (
    ObjectNameVO,
)
from src.modules.schema_registry.infrastructure.repository.data_source_repository import (
    SqlAlchemyDataSourceRepository,
)
from src.modules.schema_registry.infrastructure.repository.object_repository import (
    SqlAlchemyObjectRepository,
)
from src.modules.shared import EntityIdVO
from src.modules.shared.db.base import Base
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel


class SchemaRegistryRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)
        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self) -> None:
        await self._engine.dispose()

    async def test_object_repository_preserves_tenant_and_data_source_ids(self) -> None:
        tenant_id = uuid4()
        now = datetime.now(UTC)

        async with self._session_factory() as session:
            session.add(
                TenantModel(
                    id=tenant_id,
                    name="tenant",
                    external_id="tenant-1",
                    status="active",
                    custom_config=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.flush()

            datasource_repository = SqlAlchemyDataSourceRepository(session)
            object_repository = SqlAlchemyObjectRepository(session)

            datasource = DataSourceEntity.create(
                id_=EntityIdVO.from_value(uuid4()),
                now=now,
                tenant_id=EntityIdVO.from_value(tenant_id),
                schema_name=SchemaNameVO("dnk_test"),
            )
            await datasource_repository.add(datasource)

            object_entity = ObjectEntity.create(
                id_=EntityIdVO.from_value(uuid4()),
                tenant_id=EntityIdVO.from_value(tenant_id),
                data_source_id=datasource.id,
                now=now,
                object_name=ObjectNameVO(singular="contact", plural="contacts"),
                object_label=ObjectLabelVO(singular="Contact", plural="Contacts"),
                description="Tenant contacts.",
            )
            object_entity.add_field(
                field_id=EntityIdVO.from_value(uuid4()),
                now=now,
                field_name="last_name",
                field_type=FieldTypeService().from_seed_type("text"),
                label="Last Name",
                description="Contact last name.",
                is_nullable=False,
            )

            await object_repository.replace_all_for_tenant(
                tenant_id=EntityIdVO.from_value(tenant_id),
                objects=[object_entity],
            )

            objects = await object_repository.list_by_tenant_id(
                tenant_id=EntityIdVO.from_value(tenant_id)
            )

        self.assertEqual(len(objects), 1)
        self.assertEqual(objects[0].tenant_id, EntityIdVO.from_value(tenant_id))
        self.assertEqual(objects[0].data_source_id, datasource.id)
        self.assertEqual(objects[0].fields[0].field_name.value, "last_name")

    async def test_replace_all_flushes_objects_before_fields(self) -> None:
        tenant_id = uuid4()
        datasource_id = EntityIdVO.from_value(uuid4())
        now = datetime.now(UTC)

        object_entity = ObjectEntity.create(
            id_=EntityIdVO.from_value(uuid4()),
            tenant_id=EntityIdVO.from_value(tenant_id),
            data_source_id=datasource_id,
            now=now,
            object_name=ObjectNameVO(singular="contact", plural="contacts"),
            object_label=ObjectLabelVO(singular="Contact", plural="Contacts"),
            description="Tenant contacts.",
        )
        object_entity.add_field(
            field_id=EntityIdVO.from_value(uuid4()),
            now=now,
            field_name="last_name",
            field_type=FieldTypeService().from_seed_type("text"),
            label="Last Name",
            description="Contact last name.",
            is_nullable=False,
        )

        class ScalarsResult:
            def all(self) -> list[object]:
                return []

        class SessionSpy:
            def __init__(self) -> None:
                self.flush_snapshots: list[list[str]] = []
                self.added_types: list[str] = []

            async def scalars(self, *_args, **_kwargs):
                return ScalarsResult()

            async def execute(self, *_args, **_kwargs) -> None:
                return None

            def add(self, model) -> None:
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
            [["ObjectORM"], ["ObjectORM", "FieldORM"]],
        )
