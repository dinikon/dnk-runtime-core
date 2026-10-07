"""Проверки состава API и tenant metadata после удаления локального Catalog."""

import unittest

from fastapi import FastAPI

from src.modules.router import router
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migration_metadata import (
    migration_metadata,
)
from src.modules.tenant_persistence import HISTORICAL_TENANT_TABLE_NAMES


class ModuleRegistrationTests(unittest.TestCase):
    """Проверяет отсутствие удалённого модуля и доступность его соседей."""

    def test_routes_exclude_catalog_and_keep_inventory_and_channels(self) -> None:
        """Сборка API не содержит Catalog и сохраняет независимые модули."""
        app = FastAPI()
        app.include_router(router)
        paths = set(app.openapi()["paths"])
        self.assertFalse(any(path.startswith("/api/console/catalog") for path in paths))
        self.assertTrue(
            any(path.startswith("/api/console/inventory/skus") for path in paths)
        )
        self.assertTrue(any(path.startswith("/api/console/channels") for path in paths))

    def test_metadata_excludes_catalog_but_retains_migration_ownership(self) -> None:
        """Исторические имена таблиц не регистрируют удалённые ORM-модели."""
        tables = set(migration_metadata().tables)
        self.assertFalse(any(name.startswith("catalog_") for name in tables))
        self.assertTrue({"skus", "channels", "channel_publications"} <= tables)
        self.assertIn("catalog_products", HISTORICAL_TENANT_TABLE_NAMES)
