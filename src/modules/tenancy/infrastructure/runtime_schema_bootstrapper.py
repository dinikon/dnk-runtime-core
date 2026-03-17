from __future__ import annotations

from uuid import UUID, uuid5

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.runtime_schema.domain.entities import DataSource, ObjectMetadata
from src.modules.runtime_schema.domain.repositories import (
    DataSourceRepositoryProtocol,
    ObjectMetadataRepositoryProtocol,
)
from src.modules.runtime_schema.domain.value_objects import ObjectOwnershipKind
from src.modules.tenancy.application.ports.runtime_schema_bootstrapper import (
    RuntimeSchemaBootstrapperProtocol,
)

_CONTACT_SEED_NAMESPACE = UUID("7e0b65e5-7ad2-46b7-9cf6-4de64f2aa6d9")
_COMPANY_SEED_NAMESPACE = UUID("52d1cf7b-4727-43f4-98cc-f0e2ab3257ab")


class SqlAlchemyRuntimeSchemaBootstrapper(RuntimeSchemaBootstrapperProtocol):
    def __init__(
        self,
        *,
        session: AsyncSession,
        data_source_repository: DataSourceRepositoryProtocol,
        object_metadata_repository: ObjectMetadataRepositoryProtocol,
    ):
        self._session = session
        self._data_source_repository = data_source_repository
        self._object_metadata_repository = object_metadata_repository

    async def bootstrap_tenant(self, tenant_id: UUID) -> None:
        data_source = await self._ensure_data_source(tenant_id)
        await self._ensure_object_metadata(
            tenant_id=tenant_id,
            data_source_id=data_source.id,
            name_singular="contact",
            name_plural="contacts",
            label_singular="Contact",
            label_plural="Contacts",
        )
        await self._ensure_object_metadata(
            tenant_id=tenant_id,
            data_source_id=data_source.id,
            name_singular="company",
            name_plural="companies",
            label_singular="Company",
            label_plural="Companies",
        )

        await self._ensure_runtime_tables(schema_name=data_source.schema)
        await self._seed_runtime_records(tenant_id=tenant_id, schema_name=data_source.schema)

    async def _ensure_data_source(self, tenant_id: UUID) -> DataSource:
        existing = await self._data_source_repository.list_by_tenant_id(tenant_id)
        if existing:
            return existing[0]

        data_source = DataSource.create(tenant_id=tenant_id)
        await self._data_source_repository.add(data_source)
        return data_source

    async def _ensure_object_metadata(
        self,
        *,
        tenant_id: UUID,
        data_source_id: UUID,
        name_singular: str,
        name_plural: str,
        label_singular: str,
        label_plural: str,
    ) -> ObjectMetadata:
        existing = await self._object_metadata_repository.get_by_name(
            tenant_id=tenant_id,
            name_singular=name_singular,
        )
        if existing is not None:
            return existing

        object_metadata = ObjectMetadata.create(
            tenant_id=tenant_id,
            data_source_id=data_source_id,
            name_singular=name_singular,
            name_plural=name_plural,
            label_singular=label_singular,
            label_plural=label_plural,
            ownership_kind=ObjectOwnershipKind.MODULE,
            allows_custom_fields=True,
            is_system=True,
        )
        await self._object_metadata_repository.add(object_metadata)
        return object_metadata

    async def _ensure_runtime_tables(self, *, schema_name: str) -> None:
        dialect_name = self._session.bind.dialect.name if self._session.bind else ""

        if dialect_name == "postgresql":
            await self._session.execute(
                text(f"CREATE SCHEMA IF NOT EXISTS {_quoted_schema_name(schema_name)}")
            )

        contacts_ref = _qualified_table(
            session=self._session,
            schema_name=schema_name,
            table_name="contacts",
        )
        companies_ref = _qualified_table(
            session=self._session,
            schema_name=schema_name,
            table_name="companies",
        )
        id_type_sql = "UUID" if dialect_name == "postgresql" else "CHAR(36)"
        ts_type_sql = (
            "TIMESTAMP WITH TIME ZONE"
            if dialect_name == "postgresql"
            else "TIMESTAMP"
        )

        await self._session.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {contacts_ref} ("
                f"id {id_type_sql} PRIMARY KEY, "
                f"created_at {ts_type_sql} DEFAULT CURRENT_TIMESTAMP NOT NULL, "
                f"updated_at {ts_type_sql} DEFAULT CURRENT_TIMESTAMP NOT NULL, "
                f"last_name VARCHAR(255) NOT NULL, "
                f"first_name VARCHAR(255) NOT NULL, "
                f"middle_name VARCHAR(255)"
                ")"
            )
        )
        await self._session.execute(
            text(
                f"CREATE TABLE IF NOT EXISTS {companies_ref} ("
                f"id {id_type_sql} PRIMARY KEY, "
                f"created_at {ts_type_sql} DEFAULT CURRENT_TIMESTAMP NOT NULL, "
                f"updated_at {ts_type_sql} DEFAULT CURRENT_TIMESTAMP NOT NULL, "
                f"last_name VARCHAR(255) NOT NULL, "
                f"company_name VARCHAR(255) NOT NULL"
                ")"
            )
        )

    async def _seed_runtime_records(self, *, tenant_id: UUID, schema_name: str) -> None:
        contacts_ref = _qualified_table(
            session=self._session,
            schema_name=schema_name,
            table_name="contacts",
        )
        companies_ref = _qualified_table(
            session=self._session,
            schema_name=schema_name,
            table_name="companies",
        )
        contact_seed_id = str(uuid5(_CONTACT_SEED_NAMESPACE, str(tenant_id)))
        company_seed_id = str(uuid5(_COMPANY_SEED_NAMESPACE, str(tenant_id)))
        dialect_name = self._session.bind.dialect.name if self._session.bind else ""

        if dialect_name == "postgresql":
            contacts_insert_sql = (
                f"INSERT INTO {contacts_ref} "
                '(id, last_name, first_name, middle_name) '
                "VALUES (:id, :last_name, :first_name, :middle_name) "
                "ON CONFLICT (id) DO NOTHING"
            )
            companies_insert_sql = (
                f"INSERT INTO {companies_ref} "
                "(id, last_name, company_name) "
                "VALUES (:id, :last_name, :company_name) "
                "ON CONFLICT (id) DO NOTHING"
            )
        else:
            contacts_insert_sql = (
                f"INSERT OR IGNORE INTO {contacts_ref} "
                "(id, last_name, first_name, middle_name) "
                "VALUES (:id, :last_name, :first_name, :middle_name)"
            )
            companies_insert_sql = (
                f"INSERT OR IGNORE INTO {companies_ref} "
                "(id, last_name, company_name) "
                "VALUES (:id, :last_name, :company_name)"
            )

        await self._session.execute(
            text(contacts_insert_sql),
            {
                "id": contact_seed_id,
                "last_name": "Seed",
                "first_name": "Contact",
                "middle_name": None,
            },
        )
        await self._session.execute(
            text(companies_insert_sql),
            {
                "id": company_seed_id,
                "last_name": "Seed",
                "company_name": "Seed Company",
            },
        )


def _qualified_table(
    *,
    session: AsyncSession,
    schema_name: str | None,
    table_name: str,
) -> str:
    quoted_table = _quoted_identifier(table_name)
    dialect_name = session.bind.dialect.name if session.bind else ""

    if not schema_name or dialect_name == "sqlite":
        return quoted_table

    return f"{_quoted_schema_name(schema_name)}.{quoted_table}"


def _quoted_identifier(value: str) -> str:
    escaped = value.strip().replace('"', '""')
    return f'"{escaped}"'


def _quoted_schema_name(value: str) -> str:
    escaped = value.strip().replace('"', '""')
    return f'"{escaped}"'


__all__ = ["SqlAlchemyRuntimeSchemaBootstrapper"]
