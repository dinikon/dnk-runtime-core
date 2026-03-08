import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.modules.runtime_schema.domain.entities import (
    FieldMetadata,
    ObjectMetadata,
    RelationMetadata,
)
from src.modules.runtime_schema.domain.errors import (
    FieldMetadataNotFoundError,
    ObjectMetadataNotFoundError,
    RelationMetadataNotFoundError,
)
from src.modules.runtime_schema.domain.value_objects import RuntimeSchemaFieldType
from src.modules.runtime_schema.infrastructure.repositories import (
    SqlAlchemyFieldMetadataRepository,
    SqlAlchemyObjectMetadataRepository,
    SqlAlchemyRelationMetadataRepository,
)
from src.modules.shared.db.base import Base
from src.modules.tenancy.infrastructure.persistence.data_source import (
    TenantDataSourceModel,
)
from src.modules.tenancy.infrastructure.persistence.tenant import TenantModel


class RuntimeSchemaRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._temp_dir.name) / "runtime_schema.db"
        self._engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )
        async with self._engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        self.tenant_id = uuid4()
        self.data_source_id = uuid4()
        await self._seed_control_plane_rows()

    async def asyncTearDown(self) -> None:
        await self._engine.dispose()
        self._temp_dir.cleanup()

    async def test_repositories_roundtrip_and_filter_inactive_relations(self) -> None:
        company = ObjectMetadata.create_system(
            tenant_id=self.tenant_id,
            data_source_id=self.data_source_id,
            table_name="crm_companies",
            name_singular="company",
            name_plural="companies",
            label_singular="Company",
            label_plural="Companies",
        )
        lead = ObjectMetadata.create_system(
            tenant_id=self.tenant_id,
            data_source_id=self.data_source_id,
            table_name="crm_leads",
            name_singular="lead",
            name_plural="leads",
            label_singular="Lead",
            label_plural="Leads",
        )
        company_id_field = FieldMetadata.create_system(
            tenant_id=self.tenant_id,
            object_metadata_id=lead.id,
            field_type=RuntimeSchemaFieldType.UUID,
            name_field="company_id",
            label="Company",
            is_nullable=True,
        )
        lead_title_field = FieldMetadata.create_system(
            tenant_id=self.tenant_id,
            object_metadata_id=lead.id,
            field_type=RuntimeSchemaFieldType.STRING,
            name_field="title",
            label="Title",
            is_nullable=False,
        )
        company_pk_field = FieldMetadata.create_system(
            tenant_id=self.tenant_id,
            object_metadata_id=company.id,
            field_type=RuntimeSchemaFieldType.UUID,
            name_field="id",
            label="ID",
            is_nullable=False,
            is_unique=True,
        )
        owner_relation = RelationMetadata.create_many_to_one(
            tenant_id=self.tenant_id,
            source_object_metadata_id=lead.id,
            source_field_metadata_id=company_id_field.id,
            target_object_metadata_id=company.id,
            target_field_metadata_id=company_pk_field.id,
            reverse_name_field="leads",
            reverse_label="Leads",
            is_system=True,
        )
        junction_relation = RelationMetadata.create_many_to_many(
            tenant_id=self.tenant_id,
            source_object_metadata_id=lead.id,
            target_object_metadata_id=company.id,
            junction_table_name="rel_lead_company",
        )

        async with self._session_factory() as session:
            object_repository = SqlAlchemyObjectMetadataRepository(session)
            field_repository = SqlAlchemyFieldMetadataRepository(session)
            relation_repository = SqlAlchemyRelationMetadataRepository(session)

            await object_repository.add(company)
            await object_repository.add(lead)
            await field_repository.add(company_id_field)
            await field_repository.add(lead_title_field)
            await field_repository.add(company_pk_field)
            lead.bind_label_identifier_field(lead_title_field.id)
            await object_repository.save(lead)
            company_id_field.bind_relation(company.id, company_pk_field.id)
            await field_repository.save(company_id_field)
            await relation_repository.add(owner_relation)
            await relation_repository.add(junction_relation)
            await session.commit()

        async with self._session_factory() as session:
            object_repository = SqlAlchemyObjectMetadataRepository(session)
            field_repository = SqlAlchemyFieldMetadataRepository(session)
            relation_repository = SqlAlchemyRelationMetadataRepository(session)

            stored_lead = await object_repository.get_by_tenant_and_name_singular(
                self.tenant_id,
                "lead",
            )
            stored_company_field = await field_repository.get_by_object_and_name_field(
                lead.id,
                "company_id",
            )
            stored_owner_relation = await relation_repository.get_by_source_field_id(
                company_id_field.id
            )

            self.assertIsNotNone(stored_lead)
            self.assertIsNotNone(stored_company_field)
            self.assertIsNotNone(stored_owner_relation)
            assert stored_lead is not None
            assert stored_company_field is not None
            assert stored_owner_relation is not None
            self.assertEqual(
                stored_lead.label_identifier_field_metadata_id,
                lead_title_field.id,
            )
            self.assertEqual(
                stored_company_field.relation_target_object_metadata_id,
                company.id,
            )
            self.assertTrue(
                await relation_repository.exists_by_junction_table_name(
                    "rel_lead_company"
                )
            )

            junction_relation.deactivate()
            await relation_repository.save(junction_relation)
            await session.commit()

        async with self._session_factory() as session:
            relation_repository = SqlAlchemyRelationMetadataRepository(session)
            self.assertFalse(
                await relation_repository.exists_by_junction_table_name(
                    "rel_lead_company"
                )
            )

    async def test_save_raises_when_metadata_row_is_missing(self) -> None:
        async with self._session_factory() as session:
            object_repository = SqlAlchemyObjectMetadataRepository(session)
            field_repository = SqlAlchemyFieldMetadataRepository(session)
            relation_repository = SqlAlchemyRelationMetadataRepository(session)

            with self.assertRaises(ObjectMetadataNotFoundError):
                await object_repository.save(
                    ObjectMetadata.create_system(
                        tenant_id=self.tenant_id,
                        data_source_id=self.data_source_id,
                        table_name="crm_deals",
                        name_singular="deal",
                        name_plural="deals",
                        label_singular="Deal",
                        label_plural="Deals",
                    )
                )

            with self.assertRaises(FieldMetadataNotFoundError):
                await field_repository.save(
                    FieldMetadata.create_system(
                        tenant_id=self.tenant_id,
                        object_metadata_id=uuid4(),
                        field_type=RuntimeSchemaFieldType.STRING,
                        name_field="title",
                        label="Title",
                    )
                )

            with self.assertRaises(RelationMetadataNotFoundError):
                await relation_repository.save(
                    RelationMetadata.create_many_to_many(
                        tenant_id=self.tenant_id,
                        source_object_metadata_id=uuid4(),
                        target_object_metadata_id=uuid4(),
                        junction_table_name="rel_missing_relation",
                    )
                )

    async def _seed_control_plane_rows(self) -> None:
        now = datetime.now(UTC)
        async with self._session_factory() as session:
            session.add(
                TenantModel(
                    id=self.tenant_id,
                    name="Acme",
                    external_id="tenant-acme",
                    status="active",
                    custom_config=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                TenantDataSourceModel(
                    id=self.data_source_id,
                    tenant_id=self.tenant_id,
                    type="postgresql",
                    is_remote=False,
                    dsn=None,
                    schema="dnk_schema_test",
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.commit()
