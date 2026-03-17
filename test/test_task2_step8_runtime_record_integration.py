from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.modules.runtime_record.application import (
    ReadRuntimeValuesQuery,
    RuntimeRecordApplicationService,
    WriteRuntimeValuesCommand,
)
from src.modules.runtime_record.infrastructure import SqlAlchemyRuntimeValueRepository
from src.modules.runtime_schema.domain.entities import DataSource, FieldMetadata, ObjectMetadata
from src.modules.runtime_schema.domain.value_objects import FieldType, ObjectOwnershipKind
from src.modules.runtime_schema.infrastructure.repositories import (
    SqlAlchemyDataSourceRepository,
    SqlAlchemyFieldMetadataRepository,
    SqlAlchemyObjectMetadataRepository,
)
from src.modules.shared.db.base import Base
from src.modules.shared.db.uow import UnitOfWork


class TestRuntimeRecordIntegrationStep8(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self._temp_dir.name) / "step8_runtime_record.sqlite3"

        self._engine = create_async_engine(
            f"sqlite+aiosqlite:///{database_path}",
            future=True,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )

        self._contact_record_id = uuid4()
        self._company_record_id = uuid4()

        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            await connection.execute(text("DROP TABLE IF EXISTS contacts"))
            await connection.execute(text("DROP TABLE IF EXISTS companies"))
            await connection.execute(
                text(
                    "CREATE TABLE contacts ("
                    "id CHAR(36) PRIMARY KEY, "
                    "first_name VARCHAR(255) NOT NULL, "
                    "last_name VARCHAR(255) NOT NULL, "
                    "telegram VARCHAR(255), "
                    "tags JSON"
                    ")"
                )
            )
            await connection.execute(
                text(
                    "CREATE TABLE companies ("
                    "id CHAR(36) PRIMARY KEY, "
                    "last_name VARCHAR(255) NOT NULL, "
                    "company_name VARCHAR(255) NOT NULL, "
                    "category VARCHAR(255), "
                    "segments JSON"
                    ")"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO contacts (id, first_name, last_name) "
                    "VALUES (:id, :first_name, :last_name)"
                ),
                {
                    "id": str(self._contact_record_id),
                    "first_name": "John",
                    "last_name": "Doe",
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO companies (id, last_name, company_name) "
                    "VALUES (:id, :last_name, :company_name)"
                ),
                {
                    "id": str(self._company_record_id),
                    "last_name": "Owner",
                    "company_name": "Acme Inc.",
                },
            )

        self._tenant_id = await self._seed_runtime_metadata()

    async def asyncTearDown(self) -> None:
        await self._engine.dispose()
        self._temp_dir.cleanup()

    async def test_write_and_read_custom_values_for_contact(self) -> None:
        uow = UnitOfWork(self._session_factory)
        async with uow:
            service = self._build_service(session=uow.session, uow=uow)
            await service.write_values(
                WriteRuntimeValuesCommand(
                    tenant_id=self._tenant_id,
                    object_name_singular="contact",
                    record_id=self._contact_record_id,
                    values={
                        "telegram": "@john_doe",
                        "tags": ["vip", "partner"],
                    },
                )
            )

        uow = UnitOfWork(self._session_factory)
        async with uow:
            service = self._build_service(session=uow.session, uow=uow)
            result = await service.read_values(
                ReadRuntimeValuesQuery(
                    tenant_id=self._tenant_id,
                    object_name_singular="contact",
                    record_id=self._contact_record_id,
                )
            )

        self.assertEqual(result.values["telegram"], "@john_doe")
        self.assertEqual(result.values["tags"], ["vip", "partner"])

    async def test_write_and_read_custom_values_for_company(self) -> None:
        uow = UnitOfWork(self._session_factory)
        async with uow:
            service = self._build_service(session=uow.session, uow=uow)
            await service.write_values(
                WriteRuntimeValuesCommand(
                    tenant_id=self._tenant_id,
                    object_name_singular="company",
                    record_id=self._company_record_id,
                    values={
                        "category": "vendor",
                        "segments": ["b2b"],
                    },
                )
            )

        uow = UnitOfWork(self._session_factory)
        async with uow:
            service = self._build_service(session=uow.session, uow=uow)
            result = await service.read_values(
                ReadRuntimeValuesQuery(
                    tenant_id=self._tenant_id,
                    object_name_singular="company",
                    record_id=self._company_record_id,
                )
            )

        self.assertEqual(result.values["category"], "vendor")
        self.assertEqual(result.values["segments"], ["b2b"])

    def _build_service(
        self,
        *,
        session: AsyncSession | None,
        uow: UnitOfWork,
    ) -> RuntimeRecordApplicationService:
        assert session is not None
        return RuntimeRecordApplicationService(
            uow=uow,
            object_metadata_repository=SqlAlchemyObjectMetadataRepository(session),
            field_metadata_repository=SqlAlchemyFieldMetadataRepository(session),
            data_source_repository=SqlAlchemyDataSourceRepository(session),
            runtime_value_repository=SqlAlchemyRuntimeValueRepository(session),
        )

    async def _seed_runtime_metadata(self) -> UUID:
        tenant_id = uuid4()
        data_source = DataSource.create(tenant_id=tenant_id)

        contact_object = ObjectMetadata.create(
            tenant_id=tenant_id,
            data_source_id=data_source.id,
            name_singular="contact",
            name_plural="contacts",
            label_singular="Contact",
            label_plural="Contacts",
            ownership_kind=ObjectOwnershipKind.MODULE,
            allows_custom_fields=True,
        )
        company_object = ObjectMetadata.create(
            tenant_id=tenant_id,
            data_source_id=data_source.id,
            name_singular="company",
            name_plural="companies",
            label_singular="Company",
            label_plural="Companies",
            ownership_kind=ObjectOwnershipKind.MODULE,
            allows_custom_fields=True,
        )

        contact_fields = (
            FieldMetadata.create(
                object_metadata_id=contact_object.id,
                tenant_id=tenant_id,
                field_type=FieldType.STRING,
                name="telegram",
                label="Telegram",
                is_nullable=False,
            ),
            FieldMetadata.create(
                object_metadata_id=contact_object.id,
                tenant_id=tenant_id,
                field_type=FieldType.MULTISELECT,
                name="tags",
                label="Tags",
                options=("vip", "partner", "new"),
                is_nullable=True,
            ),
        )
        company_fields = (
            FieldMetadata.create(
                object_metadata_id=company_object.id,
                tenant_id=tenant_id,
                field_type=FieldType.SELECT,
                name="category",
                label="Category",
                options=("vendor", "partner"),
                is_nullable=False,
            ),
            FieldMetadata.create(
                object_metadata_id=company_object.id,
                tenant_id=tenant_id,
                field_type=FieldType.MULTISELECT,
                name="segments",
                label="Segments",
                options=("b2b", "enterprise"),
                is_nullable=True,
            ),
        )

        async with self._session_factory() as session:
            data_sources = SqlAlchemyDataSourceRepository(session)
            objects = SqlAlchemyObjectMetadataRepository(session)
            fields = SqlAlchemyFieldMetadataRepository(session)

            await data_sources.add(data_source)
            await objects.add(contact_object)
            await objects.add(company_object)
            for field in contact_fields:
                await fields.add(field)
            for field in company_fields:
                await fields.add(field)
            await session.commit()

        return tenant_id


if __name__ == "__main__":
    unittest.main()
