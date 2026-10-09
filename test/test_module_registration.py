"""Проверки состава API и tenant metadata после удаления Catalog и Inventory."""

import unittest
from pathlib import Path

from fastapi import FastAPI

from src.modules.router import router
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migration_metadata import (
    migration_metadata,
)
from src.modules.tenant_persistence import HISTORICAL_TENANT_TABLE_NAMES


class ModuleRegistrationTests(unittest.TestCase):
    """Проверяет отсутствие удалённого модуля и доступность его соседей."""

    def test_inventory_source_and_console_module_are_absent(self) -> None:
        """Удалённый модуль не остаётся в исходниках backend и консоли."""
        root = Path(__file__).resolve().parents[1]
        for relative_path in (
            "src/modules/inventory",
            "frontends/apps/console/src/modules/inventory",
        ):
            self.assertFalse((root / relative_path).exists())

    def test_routes_exclude_catalog_and_inventory_and_keep_channels(self) -> None:
        """Сборка API не содержит Catalog и Inventory и сохраняет Channels."""
        app = FastAPI()
        app.include_router(router)
        paths = set(app.openapi()["paths"])
        self.assertFalse(any(path.startswith("/api/console/catalog") for path in paths))
        self.assertFalse(
            any(path.startswith("/api/console/inventory") for path in paths)
        )
        self.assertTrue(any(path.startswith("/api/console/channels") for path in paths))

    def test_metadata_excludes_removed_modules_but_retains_migration_ownership(
        self,
    ) -> None:
        """Исторические имена таблиц не регистрируют удалённые ORM-модели."""
        tables = set(migration_metadata().tables)
        self.assertFalse(any(name.startswith("catalog_") for name in tables))
        self.assertTrue({"skus", "warehouses"}.isdisjoint(tables))
        self.assertTrue({"channels", "channel_publications"} <= tables)
        self.assertTrue({"skus", "warehouses"} <= HISTORICAL_TENANT_TABLE_NAMES)
        self.assertIn("catalog_products", HISTORICAL_TENANT_TABLE_NAMES)
