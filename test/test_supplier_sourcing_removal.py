"""Отключение Supplier Sourcing и обратимость структуры tenant-хранения."""

import os
from io import StringIO
from pathlib import Path
import runpy
import unittest
from uuid import uuid4

from fastapi import FastAPI
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection

from src.modules.router import router
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migration_metadata import (
    managed_table_names,
    migration_metadata,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from test.crm_postgres_support import CrmPostgresTestCase

SOURCE_TABLES = frozenset({"supplier_sources", "supplier_source_fulfillment_modes"})


def source_table_contract(connection: Connection, schema: str) -> dict[str, object]:
    """Читает столбцы, индексы и ограничения обеих таблиц для проверки downgrade."""
    inspector = inspect(connection)
    return {
        name: {
            "columns": [
                (column["name"], str(column["type"]), column["nullable"])
                for column in inspector.get_columns(name, schema=schema)
            ],
            "pk": inspector.get_pk_constraint(name, schema=schema),
            "fk": inspector.get_foreign_keys(name, schema=schema),
            "checks": inspector.get_check_constraints(name, schema=schema),
            "indexes": inspector.get_indexes(name, schema=schema),
        }
        for name in sorted(SOURCE_TABLES)
    }


class SupplierSourcingRemovalContractTests(unittest.TestCase):
    """Проверяет согласованность HTTP-сборки и metadata после отключения модуля."""

    def test_console_bootstraps_without_source_api_or_orm(self) -> None:
        """CRM остаётся доступной, а источники не попадают в OpenAPI и metadata."""
        app = FastAPI()
        app.include_router(router)
        paths = app.openapi()["paths"]
        self.assertFalse(any("supplier-sourcing" in path for path in paths))
        self.assertIn("/api/console/crm/counterparty-references", paths)
        self.assertIn("/api/console/inventory/stock-documents", paths)
        metadata = migration_metadata()
        self.assertTrue(SOURCE_TABLES.isdisjoint(metadata.tables))
        self.assertTrue(SOURCE_TABLES <= managed_table_names(metadata))
        self.assertEqual(TenantMigrator().head(), "0027_drop_supplier_sourcing")

    def test_downgrade_matches_historical_postgresql_schema(self) -> None:
        """Сравнивает восстановление с исходной миграцией без runtime ORM и БД."""
        folder = Path(__file__).resolve().parents[1] / "migrations/tenant/versions"
        original = runpy.run_path(str(folder / "0024_supplier_sources.py"))
        removal = runpy.run_path(str(folder / "0027_drop_supplier_sourcing.py"))
        statements = []
        for operation in (original["upgrade"], removal["downgrade"]):
            buffer = StringIO()
            context = MigrationContext.configure(
                dialect_name="postgresql",
                opts={"as_sql": True, "output_buffer": buffer},
            )
            with Operations.context(context):
                operation()
            statements.append(buffer.getvalue())
        self.assertEqual(statements[0], statements[1])


@unittest.skipUnless(
    os.environ.get("TEST_POSTGRES_URL"), "Требуется одноразовая PostgreSQL БД."
)
class SupplierSourcingRemovalPostgresTests(CrmPostgresTestCase):
    """Проверяет миграцию с данными и сохранение самостоятельных сценариев CRM."""

    async def test_round_trip_drops_data_restores_contract_and_isolates_tenants(
        self,
    ) -> None:
        """Проверяет 0026 → 0027 → 0026 → 0027 без изменения соседнего tenant."""
        migrator = TenantMigrator()
        schema, other_schema = self.schemas
        async with self.engine.begin() as connection:
            for name in self.schemas:
                tables = await connection.run_sync(
                    lambda sync: inspect(sync).get_table_names(schema=name)
                )
                self.assertTrue(SOURCE_TABLES.isdisjoint(tables))
                await migrator.downgrade(connection, name, "0026_stock_receipts")
                identifier = uuid4()
                await connection.execute(
                    text(
                        f'INSERT INTO "{name}".supplier_sources '
                        "(id, supplier_model_key, supplier_id, name, "
                        "default_lead_time_seconds, stock_ttl_seconds, "
                        "stale_behavior, missing_sku_behavior, is_active) "
                        "VALUES (:id, 'crm.company', :supplier, 'Source', 0, 3600, "
                        "'MARK_UNKNOWN', 'KEEP_LAST', true)"
                    ),
                    {"id": identifier, "supplier": uuid4()},
                )
                await connection.execute(
                    text(
                        f'INSERT INTO "{name}".supplier_source_fulfillment_modes '
                        "(supplier_source_id, mode) VALUES (:id, 'DROPSHIP')"
                    ),
                    {"id": identifier},
                )
            before = await connection.run_sync(source_table_contract, schema)
            await migrator.upgrade(connection, schema)
            self.assertEqual(
                await migrator.current(connection, schema), (migrator.head(),)
            )
            tables = await connection.run_sync(
                lambda sync: inspect(sync).get_table_names(schema=schema)
            )
            self.assertTrue(SOURCE_TABLES.isdisjoint(tables))
            self.assertTrue({"companies", "contacts", "stock_documents"} <= set(tables))
            self.assertEqual(
                await connection.scalar(
                    text(f'SELECT count(*) FROM "{other_schema}".supplier_sources')
                ),
                1,
            )
            self.assertEqual(
                await migrator.current(connection, other_schema),
                ("0026_stock_receipts",),
            )
            await migrator.downgrade(connection, schema, "0026_stock_receipts")
            self.assertEqual(
                await connection.run_sync(source_table_contract, schema), before
            )
            for table in SOURCE_TABLES:
                self.assertEqual(
                    await connection.scalar(
                        text(f'SELECT count(*) FROM "{schema}"."{table}"')
                    ),
                    0,
                )
            await migrator.upgrade(connection, schema)
            self.assertEqual(
                await migrator.current(connection, schema), (migrator.head(),)
            )
        response = await self.client.get(
            f"/api/console/crm/companies/{self.company['id']}"
        )
        self.assertEqual(response.status_code, 200, response.text)

    async def test_crm_lookup_and_deletion_work_without_source_storage(self) -> None:
        """Публичный поиск и удаление обоих типов контрагентов работают на head."""
        response = await self.client.post(
            "/api/console/crm/contacts",
            headers=self.headers,
            json={"first_name": "Source", "last_name": "Contact"},
        )
        self.assertEqual(response.status_code, 201, response.text)
        contact = response.json()
        for model, identifier, search in (
            ("company", self.company["id"], "ACME"),
            ("contact", contact["id"], "Contact"),
        ):
            found = await self.client.get(
                "/api/console/crm/counterparty-references",
                params={"model_key": f"crm.{model}", "search": search},
            )
            self.assertEqual(found.status_code, 200, found.text)
            self.assertEqual(found.json()["total"], 1)
            self.assertEqual(found.json()["items"][0]["id"], identifier)
            self.assertEqual(found.json()["items"][0]["model_key"], f"crm.{model}")
            collection = "companies" if model == "company" else "contacts"
            deleted = await self.client.delete(
                f"/api/console/crm/{collection}/{identifier}", headers=self.headers
            )
            self.assertEqual(deleted.status_code, 204, deleted.text)
