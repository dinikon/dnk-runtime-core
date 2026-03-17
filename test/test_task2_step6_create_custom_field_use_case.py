from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.modules.runtime_schema.application.commands import CreateCustomFieldCommand
from src.modules.runtime_schema.application.use_cases import CreateCustomFieldUseCase
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


class _FailingMigrationAdapter(SqlAlchemyRuntimeSchemaMigrationAdapter):
    def __init__(self, session: AsyncSession, *, fail_stage: str | None):
        super().__init__(session)
        self._fail_stage = fail_stage

    async def add_column(
        self,
        *,
        schema_name: str | None,
        table_name: str,
        column_name: str,
        field_type: FieldType | str,
        is_nullable: bool,
    ) -> None:
        await super().add_column(
            schema_name=schema_name,
            table_name=table_name,
            column_name=column_name,
            field_type=field_type,
            is_nullable=is_nullable,
        )
        if self._fail_stage == "ddl":
            raise RuntimeError("ddl failed")

    async def create_unique_index(
        self,
        *,
        schema_name: str | None,
        table_name: str,
        column_name: str,
        index_name: str,
    ) -> None:
        await super().create_unique_index(
            schema_name=schema_name,
            table_name=table_name,
            column_name=column_name,
            index_name=index_name,
        )
        if self._fail_stage == "index":
            raise RuntimeError("index failed")


class _FailingFieldOrchestrator(SqlAlchemyRuntimeSchemaFieldOrchestrator):
    def __init__(
        self,
        *,
        session: AsyncSession,
        data_source_repository: SqlAlchemyDataSourceRepository,
        migration_adapter: SqlAlchemyRuntimeSchemaMigrationAdapter,
        fail_stage: str | None,
    ):
        super().__init__(
            session=session,
            data_source_repository=data_source_repository,
            migration_adapter=migration_adapter,
        )
        self._fail_stage = fail_stage

    async def _backfill_default_value(
        self,
        *,
        schema_name: str | None,
        table_name: str,
        column_name: str,
        default_value: object,
    ) -> None:
        await super()._backfill_default_value(
            schema_name=schema_name,
            table_name=table_name,
            column_name=column_name,
            default_value=default_value,
        )
        if self._fail_stage == "backfill":
            raise RuntimeError("backfill failed")


class TestCreateCustomFieldUseCaseStep6(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self._temp_dir.name) / "step6_runtime_schema.sqlite3"

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
            await connection.execute(text("DROP TABLE IF EXISTS contacts"))
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

    async def test_create_custom_field_success_with_backfill_and_unique_index(self) -> None:
        tenant_id, object_metadata_id = await self._seed_runtime_object_metadata()

        uow = UnitOfWork(self._session_factory)
        async with uow:
            use_case = self._build_use_case(
                uow=uow,
                fail_stage=None,
            )

            result = await use_case.execute(
                CreateCustomFieldCommand(
                    object_metadata_id=object_metadata_id,
                    tenant_id=tenant_id,
                    field_type=FieldType.STRING,
                    name="telegram",
                    label="Telegram",
                    default_value="unknown",
                    is_nullable=True,
                    is_unique=True,
                )
            )

        self.assertEqual(result.name, "telegram")
        self.assertEqual(result.default_value, "unknown")
        self.assertTrue(result.is_unique)

        async with self._session_factory() as session:
            field_repository = SqlAlchemyFieldMetadataRepository(session)
            stored_field = await field_repository.get_by_name(
                object_metadata_id=object_metadata_id,
                name="telegram",
            )
            self.assertIsNotNone(stored_field)

            columns = await _table_columns(session=session, table_name="contacts")
            self.assertIn("telegram", columns)

            values = await _column_values(
                session=session,
                table_name="contacts",
                column_name="telegram",
            )
            self.assertEqual(values, ("unknown",))

            indexes = await _table_indexes(session=session, table_name="contacts")
            self.assertIn("uq_contacts_telegram", indexes)
            self.assertTrue(indexes["uq_contacts_telegram"])

    async def test_create_custom_field_rolls_back_on_ddl_backfill_and_index_failures(
        self,
    ) -> None:
        tenant_id, object_metadata_id = await self._seed_runtime_object_metadata()

        for stage in ("ddl", "backfill", "index"):
            with self.subTest(stage=stage):
                field_name = f"test_{stage}"
                default_value = "fallback" if stage == "backfill" else None
                is_unique = stage == "index"
                expected_error = f"{stage} failed"

                with self.assertRaisesRegex(RuntimeError, expected_error):
                    uow = UnitOfWork(self._session_factory)
                    async with uow:
                        use_case = self._build_use_case(
                            uow=uow,
                            fail_stage=stage,
                        )
                        await use_case.execute(
                            CreateCustomFieldCommand(
                                object_metadata_id=object_metadata_id,
                                tenant_id=tenant_id,
                                field_type=FieldType.STRING,
                                name=field_name,
                                label=field_name,
                                default_value=default_value,
                                is_nullable=True,
                                is_unique=is_unique,
                            )
                        )

                async with self._session_factory() as session:
                    field_repository = SqlAlchemyFieldMetadataRepository(session)
                    stored_field = await field_repository.get_by_name(
                        object_metadata_id=object_metadata_id,
                        name=field_name,
                    )
                    self.assertIsNone(stored_field)

                    columns = await _table_columns(session=session, table_name="contacts")
                    self.assertNotIn(field_name, columns)

                    indexes = await _table_indexes(session=session, table_name="contacts")
                    self.assertNotIn(f"uq_contacts_{field_name}", indexes)

    def _build_use_case(
        self,
        *,
        uow: UnitOfWork,
        fail_stage: str | None,
    ) -> CreateCustomFieldUseCase:
        session = uow.session
        assert session is not None

        data_source_repository = SqlAlchemyDataSourceRepository(session)
        object_metadata_repository = SqlAlchemyObjectMetadataRepository(session)
        field_metadata_repository = SqlAlchemyFieldMetadataRepository(session)
        migration_adapter = _FailingMigrationAdapter(session, fail_stage=fail_stage)
        field_orchestrator = _FailingFieldOrchestrator(
            session=session,
            data_source_repository=data_source_repository,
            migration_adapter=migration_adapter,
            fail_stage=fail_stage,
        )

        return CreateCustomFieldUseCase(
            uow=uow,
            object_metadata_repository=object_metadata_repository,
            field_metadata_repository=field_metadata_repository,
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


async def _column_values(
    *,
    session: AsyncSession,
    table_name: str,
    column_name: str,
) -> tuple[object, ...]:
    rows = await session.execute(
        text(f'SELECT "{column_name}" FROM "{table_name}" ORDER BY id')
    )
    return tuple(row[0] for row in rows.fetchall())


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
