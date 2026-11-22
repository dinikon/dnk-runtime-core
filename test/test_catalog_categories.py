"""Инварианты узла дерева и назначений корневой карточки."""

import unittest
from uuid import uuid4

from src.modules.catalog.domain.catalog_category.aggregate import CatalogCategory
from src.modules.catalog.domain.catalog_category.value_object.identifier import (
    CatalogCategoryIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.categories import (
    CatalogItemCategoriesVO,
)
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO


class CatalogCategoryTests(unittest.TestCase):
    def test_restore_requires_at_least_one_valid_translation(self) -> None:
        identifier = CatalogCategoryIdVO(uuid4())
        for names in (
            {},
            {"uk": "  "},
            {"uk": "Одяг", "en": "x" * 256},
        ):
            with self.subTest(names=names), self.assertRaises(InvalidCatalogValueError):
                CatalogCategory.restore(identifier, None, names)
        node = CatalogCategory.restore(identifier, None, {"uk": "Одяг"})
        node.translate(LocaleVO("en"), " Clothing ")
        self.assertEqual(node.translations["en"].name, "Clothing")
        self.assertEqual(node.translations["uk"].name, "Одяг")

    def test_move_under_grandchild_preserves_original_position(self) -> None:
        root, child, grandchild = (CatalogCategoryIdVO(uuid4()) for _ in range(3))
        node = CatalogCategory.create(root, None, LocaleVO("ru"), "Одежда")
        with self.assertRaises(CatalogConflictError):
            node.move(grandchild, {grandchild: child, child: root, root: None})
        self.assertIsNone(node.parent_id)

    def test_promotion_preserves_other_additional_categories(self) -> None:
        primary, extra, promoted = (CatalogCategoryIdVO(uuid4()) for _ in range(3))
        selection = CatalogItemCategoriesVO(primary, (extra, promoted))
        result = selection.with_primary(promoted)
        self.assertEqual(result.primary_category_id, promoted)
        self.assertCountEqual(result.additional_category_ids, (primary, extra))
        for duplicates in ((primary,), (extra, extra)):
            with (
                self.subTest(duplicates=duplicates),
                self.assertRaises(InvalidCatalogValueError),
            ):
                CatalogItemCategoriesVO(primary, duplicates)
