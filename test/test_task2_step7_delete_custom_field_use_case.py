from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.modules.runtime_schema.application.commands import (
    CreateCustomFieldCommand,
    DeleteCustomFieldCommand,
)
from src.modules.runtime_schema.application.use_cases import (
    CreateCustomFieldUseCase,
    DeleteCustomFieldUseCase,
)
from src.modules.runtime_schema.domain.entities import DataSource, ObjectMetadata
from src.modules.runtime_schema.domain.value_objects import FieldType, ObjectOwnershipKind
from src.modules.runtime_schema.infrastructure.field_orchestrator import (
    SqlAlchemyRuntimeSchemaFieldOrchestrator,
)
from src.modules.runtime_schema.infrastructure.migration_adapter import (
    SqlAlchemyRuntimeSchemaMigrationAdapter,
)
from src.modules.runtime_schema.infrastructure.repositories import (
    SqlAlchemyDataSourceRepository,
    SqlAlchemyFieldMetadataRepository,
    SqlAlchemyObjectMetadataRepository,
)
from src.modules.shared.db.base import Base
from src.modules.shared.db.uow import UnitOfWork


class TestDeleteCustomFieldUseCaseStep7(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self._temp_dir.name) / "step7_runtime_schema.sqlite3"

        self._engine = create_async_engine(
            f"sqlite+aiosqlite:///{database_path}",
            future=True,
        )
        _configure_sqlite_transactional_ddl(self._engine)

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
                    "first_name VARCHAR(255) NOT NULL, "
                    "last_name VARCHAR(255) NOT NULL"
                    ")"
                )
            )
            await connection.execute(
                text(
                    "INSERT INTO contacts (id, first_name, last_name) "
                    "VALUES (:id, :first_name, :last_name)"
                ),
                {
                    "id": str(uuid4()),
                    "first_name": "John",
                    "last_name": "Doe",
                },
            )

    async def asyncTearDown(self) -> None:
        await self._engine.dispose()
        self._temp_dir.cleanup()

    async def test_soft_delete_deactivates_metadata_and_keeps_column(self) -> None:
        tenant_id, object_metadata_id = await self._seed_runtime_object_metadata()

        uow = UnitOfWork(self._session_factory)
        async with uow:
            create_use_case = self._build_create_use_case(uow=uow)
            created = await create_use_case.execute(
                CreateCustomFieldCommand(
                    object_metadata_id=object_metadata_id,
                    tenant_id=tenant_id,
                    field_type=FieldType.STRING,
                    name="telegram",
                    label="Telegram",
                    is_nullable=True,
                    is_unique=True,
                )
            )

        uow = UnitOfWork(self._session_factory)
        async with uow:
            delete_use_case = self._build_delete_use_case(uow=uow)
            result = await delete_use_case.execute(
                DeleteCustomFieldCommand(
                    field_metadata_id=created.id,
                    hard_delete=False,
                )
            )

        self.assertFalse(result.hard_delete)
        self.assertFalse(result.deleted)
        self.assertFalse(result.is_active)

        async with self._session_factory() as session:
            field_repository = SqlAlchemyFieldMetadataRepository(session)
            field_metadata = await field_repository.get_by_id(created.id)
            self.assertIsNotNone(field_metadata)
            self.assertFalse(field_metadata.is_active)

            columns = await _table_columns(session=session, table_name="contacts")
            self.assertIn("telegram", columns)

            indexes = await _table_indexes(session=session, table_name="contacts")
            self.assertIn("uq_contacts_telegram", indexes)

    async def test_hard_delete_removes_metadata_column_and_index(self) -> None:
        tenant_id, object_metadata_id = await self._seed_runtime_object_metadata()

        uow = UnitOfWork(self._session_factory)
        async with uow:
            create_use_case = self._build_create_use_case(uow=uow)
            created = await create_use_case.execute(
                CreateCustomFieldCommand(
                    object_metadata_id=object_metadata_id,
                    tenant_id=tenant_id,
                    field_type=FieldType.STRING,
                    name="linkedin",
                    label="LinkedIn",
                    is_nullable=True,
                    is_unique=True,
                )
            )

        uow = UnitOfWork(self._session_factory)
        async with uow:
            delete_use_case = self._build_delete_use_case(uow=uow)
            result = await delete_use_case.execute(
                DeleteCustomFieldCommand(
                    field_metadata_id=created.id,
                    hard_delete=True,
                )
            )

        self.assertTrue(result.hard_delete)
        self.assertTrue(result.deleted)
        self.assertFalse(result.is_active)

        async with self._session_factory() as session:
            field_repository = SqlAlchemyFieldMetadataRepository(session)
            deleted = await field_repository.get_by_id(created.id)
            self.assertIsNone(deleted)

            columns = await _table_columns(session=session, table_name="contacts")
            self.assertNotIn("linkedin", columns)

            indexes = await _table_indexes(session=session, table_name="contacts")
            self.assertNotIn("uq_contacts_linkedin", indexes)

    def _build_create_use_case(self, *, uow: UnitOfWork) -> CreateCustomFieldUseCase:
        session = uow.session
        assert session is not None

        data_source_repository = SqlAlchemyDataSourceRepository(session)
        object_metadata_repository = SqlAlchemyObjectMetadataRepository(session)
        field_metadata_repository = SqlAlchemyFieldMetadataRepository(session)
        migration_adapter = SqlAlchemyRuntimeSchemaMigrationAdapter(session)
        field_orchestrator = SqlAlchemyRuntimeSchemaFieldOrchestrator(
            session=session,
            data_source_repository=data_source_repository,
            migration_adapter=migration_adapter,
        )

        return CreateCustomFieldUseCase(
            uow=uow,
            object_metadata_repository=object_metadata_repository,
            field_metadata_repository=field_metadata_repository,
            field_orchestrator=field_orchestrator,
        )

    def _build_delete_use_case(self, *, uow: UnitOfWork) -> DeleteCustomFieldUseCase:
        session = uow.session
        assert session is not None

        data_source_repository = SqlAlchemyDataSourceRepository(session)
        object_metadata_repository = SqlAlchemyObjectMetadataRepository(session)
        field_metadata_repository = SqlAlchemyFieldMetadataRepository(session)
        migration_adapter = SqlAlchemyRuntimeSchemaMigrationAdapter(session)
        field_orchestrator = SqlAlchemyRuntimeSchemaFieldOrchestrator(
            session=session,
            data_source_repository=data_source_repository,
            migration_adapter=migration_adapter,
        )

        return DeleteCustomFieldUseCase(
            uow=uow,
            field_metadata_repository=field_metadata_repository,
            object_metadata_repository=object_metadata_repository,
            field_orchestrator=field_orchestrator,
        )

    async def _seed_runtime_object_metadata(self) -> tuple[UUID, UUID]:
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
            data_source_repository = SqlAlchemyDataSourceRepository(session)
            object_metadata_repository = SqlAlchemyObjectMetadataRepository(session)
            await data_source_repository.add(data_source)
            await object_metadata_repository.add(object_metadata)
            await session.commit()

        return tenant_id, object_metadata.id


async def _table_columns(*, session: AsyncSession, table_name: str) -> tuple[str, ...]:
    rows = await session.execute(text(f'PRAGMA table_info("{table_name}")'))
    return tuple(str(row[1]) for row in rows.fetchall())


async def _table_indexes(*, session: AsyncSession, table_name: str) -> dict[str, bool]:
    rows = await session.execute(text(f'PRAGMA index_list("{table_name}")'))
    return {str(row[1]): bool(row[2]) for row in rows.fetchall()}


def _configure_sqlite_transactional_ddl(engine: AsyncEngine) -> None:
    @event.listens_for(engine.sync_engine, "connect")
    def _on_connect(dbapi_connection, _connection_record) -> None:
        dbapi_connection.isolation_level = None

    @event.listens_for(engine.sync_engine, "begin")
    def _on_begin(connection) -> None:
        connection.exec_driver_sql("BEGIN")


if __name__ == "__main__":
    unittest.main()
