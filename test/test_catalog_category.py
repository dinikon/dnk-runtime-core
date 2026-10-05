"""Правила Category и назначения категорий SIMPLE Product."""

import unittest
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from src.modules.catalog.application.category.command.create_category.command import (
    CreateCategoryCommand,
    CreateCategoryTranslation,
)
from src.modules.catalog.application.category.command.create_category.handler import (
    CreateCategoryHandler,
)
from src.modules.catalog.application.category.command.move_category.command import (
    MoveCategoryCommand,
)
from src.modules.catalog.application.category.command.move_category.handler import (
    MoveCategoryHandler,
)
from src.modules.catalog.application.product.command.put_product_categories.command import (
    PutProductCategoriesCommand,
)
from src.modules.catalog.application.product.command.put_product_categories.handler import (
    PutProductCategoriesHandler,
)
from src.modules.catalog.domain.category.aggregate import Category
from src.modules.catalog.domain.category.error import (
    CategoryCycleError,
    CategoryLocaleUnavailableError,
    InvalidCategoryError,
)
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.category.value_object.locale import CategoryLocaleVO
from src.modules.catalog.domain.category.value_object.translation import (
    CategoryTranslationVO,
)
from src.modules.catalog.domain.product.aggregate import Product
from src.modules.catalog.domain.product.error import InvalidProductCategoriesError
from src.modules.catalog.domain.product.value_object.identifier import (
    ProductIdVO,
    VariantIdVO,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CategoryDomainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 10, 5, tzinfo=UTC)
        self.actor = EntityIdVO(uuid4())
        self.category_id = CategoryIdVO(uuid4())

    def create(self, translations=None):
        return Category.create(
            category_id=self.category_id,
            parent_id=None,
            translations=(
                translations
                if translations is not None
                else (CategoryTranslationVO(CategoryLocaleVO("uk"), "  Назва  "),)
            ),
            actor_id=self.actor,
            now=self.now,
        )

    def test_translation_and_audit(self) -> None:
        category = self.create()
        self.assertEqual(category.translations["uk"].name, "Назва")
        self.assertEqual(category.created_by, self.actor)
        self.assertEqual(category.updated_by, self.actor)
        with self.assertRaises(TypeError):
            category.translations["ru"] = CategoryTranslationVO(
                CategoryLocaleVO("ru"), "Имя"
            )
        category.set_translation(
            CategoryTranslationVO(CategoryLocaleVO("ru"), " Имя "),
            actor_id=self.actor,
            now=self.now,
        )
        self.assertEqual(category.translations["ru"].name, "Имя")

    def test_required_unique_and_bounded_translations(self) -> None:
        with self.assertRaises(InvalidCategoryError):
            self.create(())
        item = CategoryTranslationVO(CategoryLocaleVO("uk"), "X")
        with self.assertRaises(InvalidCategoryError):
            self.create((item, item))
        for name in (" ", "x" * 256):
            with self.assertRaises(InvalidCategoryError):
                CategoryTranslationVO(CategoryLocaleVO("uk"), name)
        self.assertEqual(
            len(CategoryTranslationVO(CategoryLocaleVO("uk"), "x" * 255).name), 255
        )

    def test_product_category_invariants(self) -> None:
        product = Product.create(
            product_id=ProductIdVO(uuid4()),
            variant_id=VariantIdVO(uuid4()),
            sku_id=EntityIdVO(uuid4()),
            contents=(),
            actor_id=self.actor,
            now=self.now,
        )
        first, second = CategoryIdVO(uuid4()), CategoryIdVO(uuid4())
        for values, primary in (
            ((first,), None),
            ((), first),
            ((first, first), first),
            ((first,), second),
        ):
            with self.assertRaises(InvalidProductCategoriesError):
                product.replace_categories(
                    category_ids=values,
                    primary_category_id=primary,
                    actor_id=self.actor,
                    now=self.now,
                )
        product.replace_categories(
            category_ids=(first, second),
            primary_category_id=second,
            actor_id=self.actor,
            now=self.now,
        )
        self.assertEqual(product.primary_category_id, second)
        product.replace_categories(
            category_ids=(), primary_category_id=None, actor_id=self.actor, now=self.now
        )
        self.assertEqual(product.category_ids, ())


class CategoryApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_checks_locale_and_parent_before_write(self) -> None:
        category_id, parent_id, tenant_id = uuid4(), uuid4(), uuid4()
        repo = Mock(
            lock_tree=AsyncMock(), exists=AsyncMock(return_value=True), add=AsyncMock()
        )
        locales = Mock(is_active=AsyncMock(return_value=True))
        handler = CreateCategoryHandler(
            repo,
            locales,
            Mock(now=Mock(return_value=datetime.now(UTC))),
            Mock(new=Mock(return_value=category_id)),
        )
        result = await handler.execute(
            CreateCategoryCommand(
                EntityIdVO(tenant_id),
                EntityIdVO(uuid4()),
                parent_id,
                (CreateCategoryTranslation("uk", " Назва "),),
            )
        )
        self.assertEqual(result.id, category_id)
        repo.lock_tree.assert_awaited_once_with(EntityIdVO(tenant_id))
        repo.add.assert_awaited_once()
        locales.is_active = AsyncMock(return_value=False)
        repo.add.reset_mock()
        with self.assertRaises(CategoryLocaleUnavailableError):
            await handler.execute(
                CreateCategoryCommand(
                    EntityIdVO(tenant_id),
                    EntityIdVO(uuid4()),
                    None,
                    (CreateCategoryTranslation("uk", "Назва"),),
                )
            )
        repo.add.assert_not_awaited()

    async def test_move_checks_cycle_after_tree_lock(self) -> None:
        category_id, child_id, tenant_id = uuid4(), uuid4(), uuid4()
        repo = Mock(
            lock_tree=AsyncMock(),
            get_for_update=AsyncMock(),
            exists=AsyncMock(return_value=True),
            is_descendant=AsyncMock(return_value=True),
            save_parent=AsyncMock(),
        )
        repo.get_for_update.return_value = Category.create(
            category_id=CategoryIdVO(category_id),
            parent_id=None,
            translations=(CategoryTranslationVO(CategoryLocaleVO("uk"), "Name"),),
            actor_id=EntityIdVO(uuid4()),
            now=datetime.now(UTC),
        )
        with self.assertRaises(CategoryCycleError):
            await MoveCategoryHandler(
                repo, Mock(now=Mock(return_value=datetime.now(UTC)))
            ).execute(
                MoveCategoryCommand(
                    EntityIdVO(tenant_id),
                    CategoryIdVO(category_id),
                    CategoryIdVO(child_id),
                    EntityIdVO(uuid4()),
                )
            )
        repo.lock_tree.assert_awaited_once_with(EntityIdVO(tenant_id))
        repo.save_parent.assert_not_awaited()

    async def test_product_assignment_checks_references_before_save(self) -> None:
        actor, category_id = EntityIdVO(uuid4()), uuid4()
        product = Product.create(
            product_id=ProductIdVO(uuid4()),
            variant_id=VariantIdVO(uuid4()),
            sku_id=EntityIdVO(uuid4()),
            contents=(),
            actor_id=actor,
            now=datetime.now(UTC),
        )
        repo = Mock(
            get_for_update=AsyncMock(return_value=product), save_categories=AsyncMock()
        )
        reader = Mock(require_all=AsyncMock())
        result = await PutProductCategoriesHandler(
            repo, reader, Mock(now=Mock(return_value=datetime.now(UTC)))
        ).execute(
            PutProductCategoriesCommand(product.id, actor, (category_id,), category_id)
        )
        self.assertEqual(result.primary_category_id, category_id)
        reader.require_all.assert_awaited_once_with((category_id,))
        repo.save_categories.assert_awaited_once_with(product)
