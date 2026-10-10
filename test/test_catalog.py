"""Доменные и архитектурные проверки первого среза Catalog."""

from src.modules.catalog.domain.content_block.value_object.value_type import (
    ContentValueType,
)

import ast
import unittest
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.product.aggregate import Product, ProductKind
from src.modules.catalog.domain.product.entity.variant import Variant
from src.modules.catalog.domain.product.value_object.identifier import ProductIdVO
from src.modules.catalog.domain.product.value_object.variant_id import VariantIdVO
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.domain.content_block.value_object.identifier import (
    ContentBlockIdVO,
)
from src.modules.catalog.domain.product.value_object.schema import (
    ProductSchemaSnapshot,
    ContentBlockSnapshot,
)
from src.modules.catalog.domain.product_type.value_object.block_link import ContentScope
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
    CatalogDependencyUnavailableError,
)


class CatalogDomainTests(unittest.TestCase):
    """Проверяет инварианты, независимые переводы и фабрику восстановления."""

    def setUp(self) -> None:
        """Готовит явную схему и новый SIMPLE без переводов."""
        self.now = datetime.now(UTC)
        self.actor = EntityIdVO(uuid4())
        self.block = ContentBlockIdVO(uuid4())
        self.schema = ProductSchemaSnapshot(
            ProductTypeIdVO(uuid4()),
            1,
            (
                ContentBlockSnapshot(
                    self.block, ContentValueType.TEXT, ContentScope.PRODUCT, True, 0
                ),
                ContentBlockSnapshot(
                    self.block, ContentValueType.TEXT, ContentScope.VARIANT, False, 0
                ),
            ),
        )
        self.product = Product.create(
            ProductIdVO(uuid4()),
            self.schema,
            VariantIdVO(uuid4()),
            False,
            self.actor,
            self.now,
        )

    def test_simple_content_locales_are_independent(self) -> None:
        """Контент SIMPLE хранится только у Product с независимыми локалями."""
        self.assertEqual(self.product.translations, {})
        self.product.put_content(
            LocaleVO("ru"),
            {str(self.block): "Товар"},
            self.schema,
            ContentScope.PRODUCT,
            self.actor,
            self.now,
        )
        self.product.put_content(
            LocaleVO("en"),
            {str(self.block): "Product"},
            self.schema,
            ContentScope.PRODUCT,
            self.actor,
            self.now,
        )
        self.assertEqual(self.product.translations["en"][str(self.block)], "Product")
        self.assertEqual(self.product.variant.translations, {})
        with self.assertRaises(InvalidCatalogValueError):
            self.product.put_content(
                LocaleVO("en"),
                {},
                self.schema,
                ContentScope.PRODUCT,
                self.actor,
                self.now,
            )

    def test_simple_rejects_variant_content_without_mutating_state(self) -> None:
        """Даже пустой VARIANT-перевод SIMPLE отклоняется до изменения ревизии."""
        for values in ({}, {str(self.block): "Position"}):
            with (
                self.subTest(values=values),
                self.assertRaises(InvalidCatalogValueError),
            ):
                self.product.put_content(
                    LocaleVO("en"),
                    values,
                    self.schema,
                    ContentScope.VARIANT,
                    self.actor,
                    self.now,
                )
        with self.assertRaises(InvalidCatalogValueError):
            self.product.delete_content(
                LocaleVO("en"), ContentScope.VARIANT, self.actor, self.now
            )
        self.assertEqual(self.product.revision, 1)
        self.assertEqual(self.product.translations, {})
        self.assertEqual(self.product.variant.translations, {})

    def test_type_change_checks_all_content_without_loss(self) -> None:
        """Несовместимый тип отклоняется; исходный перевод сохраняется."""
        self.product.put_content(
            LocaleVO("ru"),
            {str(self.block): "Товар"},
            self.schema,
            ContentScope.PRODUCT,
            self.actor,
            self.now,
        )
        before = self.product.product_type_id
        with self.assertRaises(InvalidCatalogValueError):
            self.product.change_type(
                ProductSchemaSnapshot(ProductTypeIdVO(uuid4()), 1, ()),
                self.actor,
                self.now,
            )
        self.assertEqual(self.product.product_type_id, before)
        self.assertEqual(self.product.translations["ru"][str(self.block)], "Товар")

    def test_restore_rejects_unsupported_structure_and_revision(self) -> None:
        """Restore не превращает неподдержанную структуру в SIMPLE."""
        kwargs = dict(
            identifier=self.product.id,
            kind=ProductKind.SIMPLE,
            product_type_id=self.schema.product_type_id,
            variant=self.product.variant,
            translations={},
            revision=1,
            created_at=self.now,
            updated_at=self.now,
            created_by=self.actor,
            updated_by=self.actor,
        )
        self.assertEqual(Product.restore(**kwargs).variant.id, self.product.variant.id)
        with self.assertRaises(InvalidCatalogValueError):
            Product.restore(**{**kwargs, "kind": ProductKind.VARIABLE})
        for translations in ({"en": {}}, {"ru": {str(self.block): "Legacy"}}):
            with (
                self.subTest(translations=translations),
                self.assertRaises(InvalidCatalogValueError),
            ):
                Product.restore(
                    **{
                        **kwargs,
                        "variant": Variant.restore(
                            self.product.variant.id, False, False, translations
                        ),
                    }
                )
        with self.assertRaises(CatalogConflictError):
            self.product.ensure_revision(2)

    def test_downloadable_requires_file_contract(self) -> None:
        """Без файлового контракта незавершённое предложение не объявляется готовым."""
        with self.assertRaises(CatalogDependencyUnavailableError):
            self.product.set_variant_properties(True, True, self.actor, self.now)
        self.assertFalse(self.product.variant.virtual)


class CatalogArchitectureTests(unittest.TestCase):
    """Проверяет обязательные файлы, слои, аннотации и отсутствие JSON-хранения."""

    def test_architecture_and_scenario_files(self) -> None:
        """Нормативные правила проверяются независимо от функциональных сценариев."""
        root = Path("src/modules/catalog")
        for path in root.rglob("*.py"):
            text = path.read_text()
            tree = ast.parse(text)
            if path.name == "__init__.py":
                self.assertEqual(text, "", str(path))
            if "/infrastructure/persistence/models/" in str(path):
                self.assertNotIn("JSON", text, str(path))
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.assertIsNotNone(node.returns, f"{path}:{node.name}")
                    self.assertIsNotNone(ast.get_docstring(node), f"{path}:{node.name}")
                    for arg in [
                        *node.args.posonlyargs,
                        *node.args.args,
                        *node.args.kwonlyargs,
                    ]:
                        if arg.arg not in {"self", "cls"}:
                            self.assertIsNotNone(
                                arg.annotation, f"{path}:{node.name}:{arg.arg}"
                            )
                    if node.name == "__post_init__":
                        self.assertIn("/value_object/", str(path))
                if isinstance(node, ast.ImportFrom) and node.module:
                    if "/domain/" in str(path):
                        self.assertFalse(
                            any(
                                f".{layer}." in node.module
                                for layer in [
                                    "application",
                                    "infrastructure",
                                    "presentation",
                                ]
                            ),
                            str(path),
                        )
                    if "/application/" in str(path):
                        self.assertFalse(
                            any(
                                f".{layer}." in node.module
                                for layer in ["infrastructure", "presentation"]
                            ),
                            str(path),
                        )
            if "/application/" in str(path) and path.name in {"command.py", "query.py"}:
                self.assertTrue((path.parent / "handler.py").exists())
                handler_tree = ast.parse((path.parent / "handler.py").read_text())
                execute = next(
                    n
                    for n in ast.walk(handler_tree)
                    if isinstance(n, ast.AsyncFunctionDef) and n.name == "execute"
                )
                has_result = not (
                    isinstance(execute.returns, ast.Constant)
                    and execute.returns.value is None
                )
                scenario, aggregate = path.parent.name, path.parents[2].name
                http = root / "presentation" / aggregate / "http"
                self.assertTrue(
                    (http / "controller" / f"{scenario}.py").exists(), str(path)
                )
                self.assertTrue(
                    (root / "presentation" / aggregate / "depends.py").exists()
                )
                if has_result:
                    self.assertTrue((path.parent / "dto.py").exists(), str(path))
                    self.assertTrue(
                        (http / "response" / f"{scenario}.py").exists(), str(path)
                    )
                else:
                    self.assertFalse((path.parent / "dto.py").exists(), str(path))
                    self.assertFalse(
                        (http / "response" / f"{scenario}.py").exists(), str(path)
                    )
                if path.name == "command.py" and not scenario.startswith("delete_"):
                    self.assertTrue(
                        (http / "request" / f"{scenario}.py").exists(), str(path)
                    )
        from src.modules.tenancy.infrastructure.tenant.persistence.tenant_migration_metadata import (
            migration_metadata,
        )

        meta = migration_metadata()
        from sqlalchemy import JSON

        for table in meta.tables.values():
            if table.name.startswith("catalog_"):
                for column in table.columns:
                    self.assertNotIsInstance(column.type, JSON)
