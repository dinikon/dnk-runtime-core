from src.modules.catalog.application.catalog_item.creation_service import (
    CatalogItemCreationService,
)
from src.modules.catalog.application.catalog_item.creation_values import (
    CreateCatalogItemValues,
)
from src.modules.catalog.infrastructure.rich_text import Nh3RichTextSanitizer

"""Контракты tenant-схем и регрессия удаления справочников Catalog."""

from dataclasses import fields, replace
from datetime import UTC, datetime
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4
from fastapi import FastAPI
from pydantic import ValidationError
from src.modules.catalog.application.catalog_item.command.create_catalog_item.command import (
    CreateCatalogItemCommand,
)
from src.modules.catalog.application.catalog_item.command.create_catalog_item.handler import (
    CreateCatalogItemHandler,
)
from src.modules.catalog.application.product_type.facade import (
    CatalogProvisioningFacade,
)
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    CatalogNotFoundError,
    InvalidCatalogValueError,
)
from src.modules.catalog.domain.product_type.aggregate import ProductType
from src.modules.catalog.domain.product_type.value_object.schema import (
    ContentBlockSnapshot,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.presentation.catalog_item.http.request.create_catalog_item import (
    CreateCatalogItemRequest,
)
from src.modules.catalog.presentation.catalog_item.http.request.update_catalog_item import (
    UpdateCatalogItemRequest,
)
from src.modules.catalog.presentation.router import router
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.shared.infrastructure.uuid.uuid7_generator import UUID7Generator
from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migration_metadata import (
    migration_metadata,
)
from test.catalog_support import default_product_type, default_schema


class MemoryProductTypes:
    """Хранит только схему одного тестового tenant."""

    def __init__(self) -> None:
        self.product_type: ProductType | None = None
        self.additions = 0

    async def get_by_code(self, code: str) -> ProductType | None:
        """Возвращает установленный агрегат по коду."""
        return (
            self.product_type
            if self.product_type and self.product_type.code == code
            else None
        )

    async def add(self, product_type: ProductType) -> None:
        """Запоминает схему, сохраняя её идентичности."""
        self.product_type = product_type
        self.additions += 1


class CatalogProductTypeTests(unittest.IsolatedAsyncioTestCase):
    """Проверяет создание схемы и выбор типа через Application."""

    async def test_defaults_have_tenant_specific_uuids_and_real_audit(self) -> None:
        actor = EntityIdVO(uuid4())
        clock = type(
            "Clock", (), {"now": lambda self: datetime(2026, 10, 18, tzinfo=UTC)}
        )()
        left, right = MemoryProductTypes(), MemoryProductTypes()
        for repository in (left, right):
            facade = CatalogProvisioningFacade(repository, UUID7Generator(), clock)
            tenant = EntityIdVO(uuid4())
            await facade.initialize_defaults(tenant, actor)
            original = repository.product_type
            await facade.initialize_defaults(tenant, actor)
            self.assertIs(repository.product_type, original)
            self.assertEqual(repository.additions, 1)
            original.ensure_default()
            self.assertEqual(original.created_by, actor)
            self.assertEqual(original.updated_by, actor)
            identifiers = [original.id, *(block.id for block in original.blocks)]
            self.assertEqual(len(set(identifiers)), 3)
            self.assertTrue(
                all(identifier.uuid.version == 7 for identifier in identifiers)
            )
            self.assertIsNone(original.snapshot("de").label)
            self.assertTrue(
                all(block.label is None for block in original.snapshot("de").blocks)
            )
        self.assertNotEqual(left.product_type.id, right.product_type.id)
        self.assertTrue(
            {b.id for b in left.product_type.blocks}.isdisjoint(
                {b.id for b in right.product_type.blocks}
            )
        )

    async def test_incomplete_existing_default_is_an_error(self) -> None:
        repository = MemoryProductTypes()
        repository.product_type = replace(
            default_product_type(), blocks=default_product_type().blocks[:1]
        )
        facade = CatalogProvisioningFacade(repository, UUID7Generator(), AsyncMock())
        with self.assertRaises(CatalogConflictError):
            await facade.initialize_defaults(EntityIdVO(uuid4()), EntityIdVO(uuid4()))
        self.assertEqual(repository.additions, 0)

    async def test_create_resolves_code_and_does_not_initialize_missing_schema(
        self,
    ) -> None:
        schemas, repository = AsyncMock(), AsyncMock()
        schema = default_schema()
        schemas.get_by_code.return_value = schema
        now = datetime(2026, 10, 18, tzinfo=UTC)
        clock = type("Clock", (), {"now": lambda self: now})()
        handler = CreateCatalogItemHandler(
            repository,
            CatalogItemCreationService(
                schemas,
                AsyncMock(),
                AsyncMock(),
                AsyncMock(),
                Nh3RichTextSanitizer(),
                AsyncMock(),
                clock,
                UUID7Generator(),
            ),
        )
        command = CreateCatalogItemCommand(EntityIdVO(uuid4()), EntityIdVO(uuid4()))
        await handler.execute(command)
        schemas.get_by_code.assert_awaited_once_with("default")
        self.assertEqual(repository.add.call_args.args[0].product_type_id, schema.id)
        repository.add.reset_mock()
        schemas.get_by_code.side_effect = CatalogNotFoundError("Нет схемы.")
        with self.assertRaises(CatalogNotFoundError):
            await handler.execute(
                replace(
                    command,
                    product=CreateCatalogItemValues(product_type_code="missing"),
                )
            )
        repository.add.assert_not_awaited()

    async def test_content_uses_schema_codes_and_required_blocks(self) -> None:
        schema = default_schema()
        schema = replace(
            schema,
            blocks=(
                *schema.blocks,
                ContentBlockSnapshot(
                    EntityIdVO(uuid4()), "details", "rich_text", True, 3
                ),
            ),
        )
        actor = EntityIdVO(uuid4())
        now = datetime(2026, 10, 18, tzinfo=UTC)
        item = CatalogItem.create(CatalogItemIdVO(uuid4()), actor, now, schema.id)
        for values in (
            {"title": "Name"},
            {"title": "Name", "details": ""},
            {"title": "Name", "details": "Text", "unknown": "Text"},
        ):
            with self.assertRaises(InvalidCatalogValueError):
                item.update(
                    fields=frozenset({"content"}),
                    actor=actor,
                    now=now,
                    locale=LocaleVO("en"),
                    content=values,
                    schema=schema,
                    expected_schema_version=1,
                )
        item.update(
            fields=frozenset({"content"}),
            actor=actor,
            now=now,
            locale=LocaleVO("en"),
            content={"title": "Name", "details": "Text"},
            schema=schema,
            expected_schema_version=1,
        )
        self.assertEqual(item.translations["en"]["details"], "Text")


class CatalogRemovedContractsTests(unittest.TestCase):
    """Проверяет публичную границу и фактическое отсутствие SQL-моделей."""

    def test_removed_fields_routes_and_sql_tables_are_absent(self) -> None:
        removed = {
            "attributes",
            "metadata",
            "category_ids",
            "primary_category_id",
            "tag_ids",
        }
        for name in removed:
            with self.subTest(field=name), self.assertRaises(ValidationError):
                UpdateCatalogItemRequest.model_validate({name: []})
        self.assertFalse(removed & {field.name for field in fields(CatalogItem)})
        self.assertEqual(
            CreateCatalogItemRequest.model_validate(
                {"product_type_code": "custom"}
            ).product_type_code,
            "custom",
        )
        app = FastAPI()
        app.include_router(router)
        schema = app.openapi()
        self.assertFalse(
            any(
                any("/" + name in path for name in ("attributes", "categories", "tags"))
                for path in schema["paths"]
            )
        )
        query = schema["paths"]["/catalog/items"]["get"]["parameters"]
        self.assertFalse(
            {"category_id", "tag_id"} & {parameter["name"] for parameter in query}
        )
        tables = {table.name for table in migration_metadata().tables.values()}
        for name in (
            "catalog_attributes",
            "catalog_attribute_options",
            "catalog_attribute_translations",
            "catalog_attribute_option_translations",
            "catalog_categories",
            "catalog_category_translations",
            "catalog_tags",
            "catalog_tag_translations",
            "catalog_item_attributes",
            "catalog_item_attribute_options",
            "catalog_item_categories",
            "catalog_item_tags",
            "catalog_item_metadata",
            "catalog_item_variant_selections",
            "catalog_item_default_selections",
        ):
            self.assertNotIn(name, tables)
