from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.modules.runtime_schema.domain.value_objects import FieldType
from src.modules.runtime_schema.infrastructure.migration_adapter import (
    SqlAlchemyRuntimeSchemaMigrationAdapter,
)


class TestRuntimeSchemaMigrationAdapterStep5(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._temp_dir = tempfile.TemporaryDirectory()
        database_path = Path(self._temp_dir.name) / "step5_runtime_schema.sqlite3"

        self._engine = create_async_engine(
            f"sqlite+aiosqlite:///{database_path}",
            future=True,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
        )

        async with self._engine.begin() as connection:
            await connection.execute(
                text(
                    "CREATE TABLE contacts ("
                    "id CHAR(36) PRIMARY KEY, "
                    "email VARCHAR(255)"
                    ")"
                )
            )

    async def asyncTearDown(self) -> None:
        await self._engine.dispose()
        self._temp_dir.cleanup()

    async def test_add_and_drop_column(self) -> None:
        if sqlite3.sqlite_version_info < (3, 35, 0):
            self.skipTest("SQLite < 3.35 does not support ALTER TABLE DROP COLUMN")

        async with self._session_factory() as session:
            adapter = SqlAlchemyRuntimeSchemaMigrationAdapter(session)

            await adapter.add_column(
                schema_name=None,
                table_name="contacts",
                column_name="telegram",
                field_type=FieldType.STRING,
                is_nullable=True,
            )
            await session.commit()

            columns = await _table_columns(session=session, table_name="contacts")
            self.assertIn("telegram", columns)

            await adapter.drop_column(
                schema_name=None,
                table_name="contacts",
                column_name="telegram",
            )
            await session.commit()

            columns = await _table_columns(session=session, table_name="contacts")
            self.assertNotIn("telegram", columns)

    async def test_create_and_drop_unique_index(self) -> None:
        async with self._session_factory() as session:
            adapter = SqlAlchemyRuntimeSchemaMigrationAdapter(session)

            await adapter.create_unique_index(
                schema_name=None,
                table_name="contacts",
                column_name="email",
                index_name="uq_contacts_email",
            )
            await session.commit()

            indexes = await _table_indexes(session=session, table_name="contacts")
            self.assertIn("uq_contacts_email", indexes)
            self.assertTrue(indexes["uq_contacts_email"])

            await adapter.drop_index(schema_name=None, index_name="uq_contacts_email")
            await session.commit()

            indexes = await _table_indexes(session=session, table_name="contacts")
            self.assertNotIn("uq_contacts_email", indexes)

    async def test_multiselect_type_mapping_uses_jsonb_for_postgresql(self) -> None:
        self.assertEqual(
            SqlAlchemyRuntimeSchemaMigrationAdapter.sql_type_for_dialect(
                FieldType.MULTISELECT,
                "postgresql",
            ),
            "JSONB",
        )
        self.assertEqual(
            SqlAlchemyRuntimeSchemaMigrationAdapter.sql_type_for_dialect(
                FieldType.MULTISELECT,
                "sqlite",
            ),
            "JSON",
        )

    async def test_add_multiselect_column_uses_json_on_sqlite(self) -> None:
        async with self._session_factory() as session:
            adapter = SqlAlchemyRuntimeSchemaMigrationAdapter(session)

            await adapter.add_column(
                schema_name=None,
                table_name="contacts",
                column_name="segments",
                field_type=FieldType.MULTISELECT,
                is_nullable=True,
            )
            await session.commit()

            columns = await _table_columns_with_types(
                session=session,
                table_name="contacts",
            )
            self.assertEqual(columns["segments"], "JSON")


async def _table_columns(*, session, table_name: str) -> tuple[str, ...]:
    rows = await session.execute(text(f'PRAGMA table_info("{table_name}")'))
    result = rows.fetchall()
    return tuple(str(row[1]) for row in result)


async def _table_columns_with_types(*, session, table_name: str) -> dict[str, str]:
    rows = await session.execute(text(f'PRAGMA table_info("{table_name}")'))
    result = rows.fetchall()
    return {str(row[1]): str(row[2]).upper() for row in result}


async def _table_indexes(*, session, table_name: str) -> dict[str, bool]:
    rows = await session.execute(text(f'PRAGMA index_list("{table_name}")'))
    result = rows.fetchall()
    return {str(row[1]): bool(row[2]) for row in result}


if __name__ == "__main__":
    unittest.main()
