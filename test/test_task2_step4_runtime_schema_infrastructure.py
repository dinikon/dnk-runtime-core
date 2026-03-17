from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.modules.runtime_schema.domain.entities import (
    DataSource,
    FieldMetadata,
    ObjectMetadata,
)
from src.modules.runtime_schema.domain.value_objects import FieldType, ObjectOwnershipKind
from src.modules.runtime_schema.infrastructure.repositories import (
    SqlAlchemyDataSourceRepository,
    SqlAlchemyFieldMetadataRepository,
    SqlAlchemyObjectMetadataRepository,
)
from src.modules.shared.db.base import Base


class TestRuntimeSchemaInfrastructureStep4(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self._temp_dir.name) / "step4_runtime_schema.sqlite3"

        self._engine = create_async_engine(
            f"sqlite+aiosqlite:///{database_path}",
            future=True,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )

        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self) -> None:
        await self._engine.dispose()
        self._temp_dir.cleanup()

    async def test_data_source_repository_crud(self) -> None:
        tenant_id = uuid4()
        data_source = DataSource.create(tenant_id=tenant_id)

        async with self._session_factory() as session:
            repository = SqlAlchemyDataSourceRepository(session)

            await repository.add(data_source)
            fetched = await repository.get_by_id(data_source.id)
            listed = await repository.list_by_tenant_id(tenant_id)
            deleted = await repository.delete_by_id(data_source.id)
            missing = await repository.get_by_id(data_source.id)

            self.assertIsNotNone(fetched)
            self.assertEqual(fetched.id, data_source.id)
            self.assertEqual(len(listed), 1)
            self.assertEqual(listed[0].id, data_source.id)
            self.assertTrue(deleted)
            self.assertIsNone(missing)

    async def test_object_metadata_repository_crud(self) -> None:
        tenant_id = uuid4()
        data_source = DataSource.create(tenant_id=tenant_id)
        object_metadata = ObjectMetadata.create(
            tenant_id=tenant_id,
            data_source_id=data_source.id,
            name_singular="contact",
            name_plural="contacts",
            label_singular="Contact",
            label_plural="Contacts",
            ownership_kind=ObjectOwnershipKind.MODULE,
            allows_custom_fields=True,
        )

        async with self._session_factory() as session:
            data_sources = SqlAlchemyDataSourceRepository(session)
            objects = SqlAlchemyObjectMetadataRepository(session)

            await data_sources.add(data_source)
            await objects.add(object_metadata)

            fetched_by_id = await objects.get_by_id(object_metadata.id)
            fetched_by_name = await objects.get_by_name(
                tenant_id=tenant_id,
                name_singular="contact",
            )
            listed = await objects.list_by_tenant_id(tenant_id)

            self.assertIsNotNone(fetched_by_id)
            self.assertEqual(fetched_by_id.id, object_metadata.id)
            self.assertIsNotNone(fetched_by_name)
            self.assertEqual(fetched_by_name.id, object_metadata.id)
            self.assertEqual(len(listed), 1)

    async def test_field_metadata_repository_crud(self) -> None:
        tenant_id = uuid4()
        data_source = DataSource.create(tenant_id=tenant_id)
        object_metadata = ObjectMetadata.create(
            tenant_id=tenant_id,
            data_source_id=data_source.id,
            name_singular="company",
            name_plural="companies",
            label_singular="Company",
            label_plural="Companies",
            ownership_kind=ObjectOwnershipKind.MODULE,
            allows_custom_fields=True,
        )
        field_metadata = FieldMetadata.create(
            object_metadata_id=object_metadata.id,
            tenant_id=tenant_id,
            field_type=FieldType.STRING,
            name="telegram",
            label="Telegram",
        )

        async with self._session_factory() as session:
            data_sources = SqlAlchemyDataSourceRepository(session)
            objects = SqlAlchemyObjectMetadataRepository(session)
            fields = SqlAlchemyFieldMetadataRepository(session)

            await data_sources.add(data_source)
            await objects.add(object_metadata)
            await fields.add(field_metadata)

            fetched_by_id = await fields.get_by_id(field_metadata.id)
            fetched_by_name = await fields.get_by_name(
                object_metadata_id=object_metadata.id,
                name="telegram",
            )
            listed = await fields.list_by_object_metadata_id(object_metadata.id)
            deleted = await fields.delete_by_id(field_metadata.id)
            missing = await fields.get_by_id(field_metadata.id)

            self.assertIsNotNone(fetched_by_id)
            self.assertEqual(fetched_by_id.id, field_metadata.id)
            self.assertIsNotNone(fetched_by_name)
            self.assertEqual(fetched_by_name.id, field_metadata.id)
            self.assertEqual(len(listed), 1)
            self.assertTrue(deleted)
            self.assertIsNone(missing)

    async def test_field_name_must_be_unique_within_object(self) -> None:
        tenant_id = uuid4()
        data_source = DataSource.create(tenant_id=tenant_id)
        object_metadata = ObjectMetadata.create(
            tenant_id=tenant_id,
            data_source_id=data_source.id,
            name_singular="lead",
            name_plural="leads",
            label_singular="Lead",
            label_plural="Leads",
            ownership_kind=ObjectOwnershipKind.MODULE,
            allows_custom_fields=True,
        )
        field_one = FieldMetadata.create(
            object_metadata_id=object_metadata.id,
            tenant_id=tenant_id,
            field_type=FieldType.STRING,
            name="telegram",
            label="Telegram",
        )
        field_two = FieldMetadata.create(
            object_metadata_id=object_metadata.id,
            tenant_id=tenant_id,
            field_type=FieldType.STRING,
            name="telegram",
            label="Telegram 2",
        )

        async with self._session_factory() as session:
            data_sources = SqlAlchemyDataSourceRepository(session)
            objects = SqlAlchemyObjectMetadataRepository(session)
            fields = SqlAlchemyFieldMetadataRepository(session)

            await data_sources.add(data_source)
            await objects.add(object_metadata)
            await fields.add(field_one)

            with self.assertRaises(IntegrityError):
                await fields.add(field_two)


if __name__ == "__main__":
    unittest.main()
