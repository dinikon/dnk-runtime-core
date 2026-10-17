"""Проверки состава API и tenant metadata после первого среза Catalog и удаления Inventory."""

import unittest
from pathlib import Path

from fastapi import FastAPI

from src.modules.router import router
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migration_metadata import (
    migration_metadata,
)
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migrations import (
    TenantMigrator,
)
from src.modules.tenant_persistence import HISTORICAL_TENANT_TABLE_NAMES


class ModuleRegistrationTests(unittest.TestCase):
    """Проверяет отсутствие удалённого модуля и доступность его соседей."""

    def test_inventory_source_and_console_module_are_absent(self) -> None:
        """Удалённый модуль не остаётся в исходниках backend и консоли."""
        root = Path(__file__).resolve().parents[1]
        for relative_path in (
            "src/modules/inventory",
            "src/modules/warehousing",
            "frontends/apps/console/src/modules/inventory",
        ):
            self.assertFalse((root / relative_path).exists())

    def test_routes_include_catalog_and_channels_but_exclude_inventory(self) -> None:
        """Сборка API содержит Catalog и Channels, Inventory отсутствует."""
        app = FastAPI()
        app.include_router(router)
        paths = set(app.openapi()["paths"])
        self.assertTrue(any(path.startswith("/api/console/catalog") for path in paths))
        self.assertFalse(
            any(path.startswith("/api/console/inventory") for path in paths)
        )
        self.assertTrue(any(path.startswith("/api/console/channels") for path in paths))
        self.assertTrue(
            {"/api/console/files/providers/", "/api/console/files/buckets/"} <= paths
        )
        self.assertFalse(
            any(path.startswith("/api/console/warehousing") for path in paths)
        )

    def test_metadata_excludes_removed_modules_but_retains_migration_ownership(
        self,
    ) -> None:
        """Исторические имена таблиц не регистрируют удалённые ORM-модели."""
        tables = set(migration_metadata().tables)
        self.assertTrue(
            {
                "catalog_item",
                "catalog_item_translations",
                "catalog_item_content_values",
            }
            <= tables
        )
        self.assertTrue({"skus", "warehouses"}.isdisjoint(tables))
        self.assertTrue({"channels", "channel_publications"} <= tables)
        self.assertTrue(
            {"files_providers", "files_buckets", "files_registry"} <= tables
        )
        self.assertFalse(any(name.startswith("warehousing_") for name in tables))
        self.assertIn("warehousing_warehouses", HISTORICAL_TENANT_TABLE_NAMES)
        self.assertTrue({"skus", "warehouses"} <= HISTORICAL_TENANT_TABLE_NAMES)
        self.assertIn("catalog_products", HISTORICAL_TENANT_TABLE_NAMES)

    def test_cancelled_warehousing_migrations_are_absent(self) -> None:
        """Warehousing отсутствует; fresh Catalog присутствует в единой tenant-цепочке."""
        from alembic.config import Config
        from alembic.script import ScriptDirectory

        config = Config()
        config.set_main_option("script_location", "migrations/tenant")
        script = ScriptDirectory.from_config(config)
        self.assertEqual(len(script.get_heads()), 1)
        self.assertIn(
            "0023_catalog_item", {r.revision for r in script.walk_revisions()}
        )
        directory = Path(__file__).resolve().parents[1] / "migrations/tenant/versions"
        for name in ("0017_warehousing_warehouses.py", "0018_warehousing_zones.py"):
            self.assertFalse((directory / name).exists())
