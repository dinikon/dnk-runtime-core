from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.modules.crm.application import (
    CreateCompanyCommand,
    CreateCompanyUseCase,
    CreateContactCommand,
    CreateContactUseCase,
    GetCompanyQuery,
    GetCompanyUseCase,
    GetContactQuery,
    GetContactUseCase,
    UpdateCompanyCommand,
    UpdateCompanyUseCase,
    UpdateContactCommand,
    UpdateContactUseCase,
)
from src.modules.crm.infrastructure import (
    SqlAlchemyCompanyRepository,
    SqlAlchemyContactRepository,
)
from src.modules.runtime_record.application import RuntimeRecordApplicationService
from src.modules.runtime_record.domain.errors import RuntimeRecordValidationError
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


class TestCrmRuntimeRecordIntegrationStep10(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self._temp_dir.name) / "step10_crm_runtime_record.sqlite3"

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
            await connection.execute(
                text(
                    "CREATE TABLE contacts ("
                    "id CHAR(36) PRIMARY KEY, "
                    "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, "
                    "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, "
                    "last_name VARCHAR(255) NOT NULL, "
                    "first_name VARCHAR(255) NOT NULL, "
                    "middle_name VARCHAR(255)"
                    ")"
                )
            )
            await connection.execute(
                text(
                    "CREATE TABLE companies ("
                    "id CHAR(36) PRIMARY KEY, "
                    "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, "
                    "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL, "
                    "last_name VARCHAR(255) NOT NULL, "
                    "company_name VARCHAR(255) NOT NULL"
                    ")"
                )
            )
            await connection.execute(text('ALTER TABLE "contacts" ADD COLUMN "telegram" VARCHAR(255)'))
            await connection.execute(text('ALTER TABLE "contacts" ADD COLUMN "tags" JSON'))
            await connection.execute(text('ALTER TABLE "companies" ADD COLUMN "category" VARCHAR(255)'))
            await connection.execute(text('ALTER TABLE "companies" ADD COLUMN "segments" JSON'))

        self._tenant_id = await self._seed_runtime_metadata()

    async def asyncTearDown(self) -> None:
        await self._engine.dispose()
        self._temp_dir.cleanup()

    async def test_atomicity_when_custom_fields_fail_core_is_rolled_back(self) -> None:
        command = CreateContactCommand(
            last_name="Doe",
            first_name="John",
            tenant_id=self._tenant_id,
            custom_fields={"unknown_field": "value"},
        )

        with self.assertRaises(RuntimeRecordValidationError):
            uow = UnitOfWork(self._session_factory)
            async with uow:
                runtime_service = self._build_runtime_record_service(
                    session=uow.session,
                    uow=uow,
                )
                use_case = CreateContactUseCase(
                    uow=uow,
                    contact_repository=SqlAlchemyContactRepository(uow.session),
                    runtime_record_service=runtime_service,
                )
                await use_case.execute(command)

        async with self._session_factory() as session:
            count = await _count_rows(session=session, table_name="contacts")
            self.assertEqual(count, 0)

    async def test_assembled_dto_contains_core_and_custom_fields_for_contact_and_company(
        self,
    ) -> None:
        uow = UnitOfWork(self._session_factory)
        async with uow:
            runtime_service = self._build_runtime_record_service(
                session=uow.session,
                uow=uow,
            )
            contact_create = CreateContactUseCase(
                uow=uow,
                contact_repository=SqlAlchemyContactRepository(uow.session),
                runtime_record_service=runtime_service,
            )
            company_create = CreateCompanyUseCase(
                uow=uow,
                company_repository=SqlAlchemyCompanyRepository(uow.session),
                runtime_record_service=runtime_service,
            )

            created_contact = await contact_create.execute(
                CreateContactCommand(
                    last_name="Doe",
                    first_name="John",
                    tenant_id=self._tenant_id,
                    custom_fields={
                        "telegram": "@john_doe",
                        "tags": ["vip"],
                    },
                )
            )
            created_company = await company_create.execute(
                CreateCompanyCommand(
                    last_name="Owner",
                    company_name="Acme",
                    tenant_id=self._tenant_id,
                    custom_fields={
                        "category": "vendor",
                        "segments": ["b2b"],
                    },
                )
            )

        uow = UnitOfWork(self._session_factory)
        async with uow:
            runtime_service = self._build_runtime_record_service(
                session=uow.session,
                uow=uow,
            )
            contact_update = UpdateContactUseCase(
                uow=uow,
                contact_repository=SqlAlchemyContactRepository(uow.session),
                runtime_record_service=runtime_service,
            )
            company_update = UpdateCompanyUseCase(
                uow=uow,
                company_repository=SqlAlchemyCompanyRepository(uow.session),
                runtime_record_service=runtime_service,
            )
            await contact_update.execute(
                UpdateContactCommand(
                    contact_id=created_contact.id,
                    last_name="Roe",
                    first_name="Jane",
                    middle_name=None,
                    tenant_id=self._tenant_id,
                    custom_fields={
                        "telegram": "@jane_roe",
                        "tags": ["partner", "vip"],
                    },
                )
            )
            await company_update.execute(
                UpdateCompanyCommand(
                    company_id=created_company.id,
                    last_name="Director",
                    company_name="Acme Corp",
                    tenant_id=self._tenant_id,
                    custom_fields={
                        "category": "partner",
                        "segments": ["enterprise", "b2b"],
                    },
                )
            )

        uow = UnitOfWork(self._session_factory)
        async with uow:
            runtime_service = self._build_runtime_record_service(
                session=uow.session,
                uow=uow,
            )
            contact_get = GetContactUseCase(
                contact_repository=SqlAlchemyContactRepository(uow.session),
                runtime_record_service=runtime_service,
            )
            company_get = GetCompanyUseCase(
                company_repository=SqlAlchemyCompanyRepository(uow.session),
                runtime_record_service=runtime_service,
            )

            contact_result = await contact_get.execute(
                GetContactQuery(
                    contact_id=created_contact.id,
                    tenant_id=self._tenant_id,
                )
            )
            company_result = await company_get.execute(
                GetCompanyQuery(
                    company_id=created_company.id,
                    tenant_id=self._tenant_id,
                )
            )

        self.assertEqual(contact_result.first_name, "Jane")
        self.assertEqual(contact_result.last_name, "Roe")
        self.assertEqual(contact_result.custom_fields["telegram"], "@jane_roe")
        self.assertEqual(contact_result.custom_fields["tags"], ["partner", "vip"])

        self.assertEqual(company_result.last_name, "Director")
        self.assertEqual(company_result.company_name, "Acme Corp")
        self.assertEqual(company_result.custom_fields["category"], "partner")
        self.assertEqual(
            company_result.custom_fields["segments"],
            ["enterprise", "b2b"],
        )

    def _build_runtime_record_service(
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

        fields = (
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
                options=("vip", "partner"),
                is_nullable=True,
            ),
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
            field_repository = SqlAlchemyFieldMetadataRepository(session)

            await data_sources.add(data_source)
            await objects.add(contact_object)
            await objects.add(company_object)
            for field in fields:
                await field_repository.add(field)
            await session.commit()

        return tenant_id


async def _count_rows(*, session: AsyncSession, table_name: str) -> int:
    rows = await session.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
    return int(rows.scalar_one())


if __name__ == "__main__":
    unittest.main()
