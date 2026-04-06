from __future__ import annotations

import sys
import types
import unittest

from src.modules.schema_registry.application.service.schema_seed_service import (
    SchemaSeedService,
)
from src.modules.schema_registry.domain.error import SeedValidationError
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.seed.field_seed import FieldSeed
from src.modules.schema_registry.domain.seed.object_seed import ObjectSeed
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed
from src.modules.schema_registry.infrastructure.seed.python_module_seed_reader import (
    PythonModuleSeedReader,
)


def make_seed(*, fields: tuple[FieldSeed, ...]) -> SchemaSeed:
    return SchemaSeed(
        version=None,
        code="crm",
        label="CRM",
        objects=(
            ObjectSeed(
                singular_name="contact",
                plural_name="contacts",
                singular_label="Contact",
                plural_label="Contacts",
                description="Tenant contacts.",
                fields=fields,
            ),
        ),
    )


class SchemaSeedServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_loads_seed_from_python_module(self) -> None:
        module_name = "test_schema_seed_valid_module"
        module = types.ModuleType(module_name)
        module.SCHEMA_SEED = make_seed(
            fields=(
                FieldSeed(name="id", type="uuid", label="ID", is_nullable=False),
                FieldSeed(
                    name="last_name",
                    type="text",
                    label="Last Name",
                    is_nullable=False,
                ),
            )
        )
        sys.modules[module_name] = module

        try:
            service = SchemaSeedService(
                PythonModuleSeedReader(),
                FieldTypeCatalog(),
            )
            seed = await service.load(seed_path=module_name)
        finally:
            sys.modules.pop(module_name, None)

        self.assertEqual(seed.objects[0].plural_name, "contacts")

    async def test_rejects_duplicate_field_names(self) -> None:
        module_name = "test_schema_seed_duplicate_fields"
        module = types.ModuleType(module_name)
        module.SCHEMA_SEED = make_seed(
            fields=(
                FieldSeed(name="id", type="uuid", label="ID", is_nullable=False),
                FieldSeed(
                    name="id",
                    type="text",
                    label="Duplicate",
                    is_nullable=False,
                ),
            )
        )
        sys.modules[module_name] = module

        try:
            service = SchemaSeedService(
                PythonModuleSeedReader(),
                FieldTypeCatalog(),
            )
            with self.assertRaises(SeedValidationError):
                await service.load(seed_path=module_name)
        finally:
            sys.modules.pop(module_name, None)
