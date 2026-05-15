from __future__ import annotations

import sys
import types
import unittest

from src.modules.schema_registry.application.service.schema_seed_service import (
    SchemaSeedService,
)
from src.modules.schema_registry.domain.error import SeedValidationError
from src.modules.schema_registry.domain.field.type_catalog import FieldTypeCatalog
from src.modules.schema_registry.domain.field.value_object.field_kind import FieldKind
from src.modules.schema_registry.domain.object.value_object.object_kind import (
    ObjectKind,
)
from src.modules.schema_registry.domain.seed.field_seed import FieldSeed
from src.modules.schema_registry.domain.seed.index_seed import IndexSeed
from src.modules.schema_registry.domain.seed.object_seed import ObjectSeed
from src.modules.schema_registry.domain.seed.relation_seed import RelationSeed
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
        module.SCHEMA_SEED = SchemaSeed(
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
                    kind="standard",
                    fields=(
                        FieldSeed(
                            name="id",
                            type="uuid",
                            label="ID",
                            is_nullable=False,
                            kind="system",
                        ),
                        FieldSeed(
                            name="last_name",
                            type="text",
                            label="Last Name",
                            is_nullable=False,
                        ),
                    ),
                ),
            ),
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
        self.assertEqual(seed.objects[0].kind, ObjectKind.STANDARD)
        self.assertEqual(seed.objects[0].fields[0].kind, FieldKind.SYSTEM)
        self.assertEqual(seed.objects[0].fields[1].kind, FieldKind.STANDARD)

    async def test_rejects_invalid_object_kind(self) -> None:
        module_name = "test_schema_seed_invalid_object_kind"
        module = types.ModuleType(module_name)
        module.SCHEMA_SEED = SchemaSeed(
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
                    kind="standart",
                    fields=(
                        FieldSeed(
                            name="id",
                            type="uuid",
                            label="ID",
                            is_nullable=False,
                        ),
                    ),
                ),
            ),
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

    async def test_rejects_invalid_field_kind(self) -> None:
        module_name = "test_schema_seed_invalid_field_kind"
        module = types.ModuleType(module_name)
        module.SCHEMA_SEED = make_seed(
            fields=(
                FieldSeed(
                    name="id",
                    type="uuid",
                    label="ID",
                    is_nullable=False,
                    kind="standart",
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

    async def test_rejects_non_custom_object_with_custom_prefix(self) -> None:
        module_name = "test_schema_seed_reserved_custom_prefix"
        module = types.ModuleType(module_name)
        module.SCHEMA_SEED = SchemaSeed(
            version=None,
            code="crm",
            label="CRM",
            objects=(
                ObjectSeed(
                    singular_name="c_contact",
                    plural_name="c_contacts",
                    singular_label="Contact",
                    plural_label="Contacts",
                    description="Tenant contacts.",
                    kind="standard",
                    fields=(
                        FieldSeed(
                            name="id",
                            type="uuid",
                            label="ID",
                            is_nullable=False,
                        ),
                    ),
                ),
            ),
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

    async def test_rejects_options_for_non_select_field(self) -> None:
        module_name = "test_schema_seed_text_options"
        module = types.ModuleType(module_name)
        module.SCHEMA_SEED = make_seed(
            fields=(
                FieldSeed(
                    name="last_name",
                    type="text",
                    label="Last Name",
                    options={"a": "A"},
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

    async def test_rejects_unsupported_relation_type(self) -> None:
        module_name = "test_schema_seed_unsupported_relation"
        module = types.ModuleType(module_name)
        module.SCHEMA_SEED = SchemaSeed(
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
                            name="company_id",
                            type="reference",
                            label="Company ID",
                            is_nullable=False,
                        ),
                    ),
                    relations=(
                        RelationSeed(
                            name="contacts_companies",
                            relation_type="belongs_to",
                            source_object="contact",
                            target_object="company",
                            owning_object="contact",
                            fk_field="company_id",
                            referenced_object="company",
                        ),
                    ),
                ),
            ),
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

    async def test_rejects_fk_relation_when_field_is_not_reference(self) -> None:
        module_name = "test_schema_seed_non_reference_fk"
        module = types.ModuleType(module_name)
        module.SCHEMA_SEED = SchemaSeed(
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
                            name="company_id",
                            type="uuid",
                            label="Company ID",
                            is_nullable=False,
                        ),
                    ),
                    relations=(
                        RelationSeed(
                            name="contacts_company",
                            relation_type="many_to_one",
                            source_object="contact",
                            target_object="company",
                            owning_object="contact",
                            fk_field="company_id",
                            referenced_object="company",
                        ),
                    ),
                ),
            ),
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

    async def test_rejects_self_many_to_many_relation(self) -> None:
        module_name = "test_schema_seed_self_many_to_many"
        module = types.ModuleType(module_name)
        module.SCHEMA_SEED = SchemaSeed(
            version=None,
            code="crm",
            label="CRM",
            objects=(
                ObjectSeed(
                    singular_name="tag",
                    plural_name="tags",
                    singular_label="Tag",
                    plural_label="Tags",
                    description="Tags.",
                    fields=(
                        FieldSeed(
                            name="id", type="uuid", label="ID", is_nullable=False
                        ),
                    ),
                    relations=(
                        RelationSeed(
                            name="related_tags",
                            relation_type="many_to_many",
                            source_object="tag",
                            target_object="tag",
                            relation_table_name="related_tags",
                        ),
                    ),
                ),
            ),
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

    async def test_rejects_global_index_name_collision(self) -> None:
        module_name = "test_schema_seed_index_collision"
        module = types.ModuleType(module_name)
        module.SCHEMA_SEED = SchemaSeed(
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
                    indexes=(IndexSeed(name="duplicate_idx", fields=("id",)),),
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
                    ),
                    indexes=(IndexSeed(name="duplicate_idx", fields=("id",)),),
                ),
            ),
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

    async def test_rejects_generated_relation_index_name_collision(self) -> None:
        module_name = "test_schema_seed_generated_index_collision"
        module = types.ModuleType(module_name)
        module.SCHEMA_SEED = SchemaSeed(
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
                            name="company_id",
                            type="reference",
                            label="Company ID",
                            is_nullable=False,
                        ),
                    ),
                    indexes=(
                        IndexSeed(
                            name="uq_contacts_company_id",
                            fields=("company_id",),
                            is_unique=False,
                        ),
                    ),
                    relations=(
                        RelationSeed(
                            name="contacts_company",
                            relation_type="one_to_one",
                            source_object="contact",
                            target_object="company",
                            owning_object="contact",
                            fk_field="company_id",
                            referenced_object="company",
                        ),
                    ),
                ),
            ),
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
