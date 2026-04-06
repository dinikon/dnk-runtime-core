from __future__ import annotations

import unittest

from src.modules.schema_registry.domain.migration.diff_service import SchemaDiffService
from src.modules.schema_registry.domain.migration.operations import (
    AddForeignKeyOperation,
    CreateTableOperation,
)
from src.modules.schema_registry.domain.seed.field_seed import FieldSeed
from src.modules.schema_registry.domain.seed.object_seed import ObjectSeed
from src.modules.schema_registry.domain.seed.relation_seed import RelationSeed
from src.modules.schema_registry.domain.seed.schema_seed import SchemaSeed


class SchemaDiffServiceTests(unittest.TestCase):
    def test_build_create_plan_uses_plural_name_for_tables(self) -> None:
        seed = SchemaSeed(
            version=None,
            code="crm",
            label="CRM",
            objects=(
                ObjectSeed(
                    singular_name="company",
                    plural_name="companies",
                    singular_label="Company",
                    plural_label="Companies",
                    description="Companies.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                    ),
                ),
                ObjectSeed(
                    singular_name="contact",
                    plural_name="contacts",
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Contacts.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                        FieldSeed(
                            name="company_id",
                            type="uuid",
                            label="Company ID",
                            is_nullable=False,
                        ),
                    ),
                    relations=(
                        RelationSeed(
                            name="contacts_company_id_fk",
                            relation_type="many_to_one",
                            source_field="company_id",
                            target_object="company",
                        ),
                    ),
                ),
            ),
        )

        plan = SchemaDiffService().build_create_plan(
            schema_name="dnk_test",
            seed=seed,
        )

        create_tables = [
            operation.table_name
            for operation in plan.operations
            if isinstance(operation, CreateTableOperation)
        ]
        foreign_keys = [
            operation
            for operation in plan.operations
            if isinstance(operation, AddForeignKeyOperation)
        ]

        self.assertEqual(create_tables, ["companies", "contacts"])
        self.assertEqual(foreign_keys[0].table_name, "contacts")
        self.assertEqual(foreign_keys[0].target_table_name, "companies")
