"""Инварианты общих enum-значений и классификации Catalog."""

import unittest
from dataclasses import replace
from uuid import uuid4
from test import test_catalog_variable as support
from src.modules.catalog.domain.category.aggregate import Category
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.tag.aggregate import Tag
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from src.modules.catalog.domain.product.value_object.attribute_value import (
    ProductAttributeValueVO,
)
from src.modules.catalog.domain.product.value_object.attribute_snapshot import (
    EnumAttributeSnapshot,
)
from src.modules.catalog.domain.product.entity.structure import SimpleProductStructure
from src.modules.catalog.domain.product.entity.variant import Variant
from src.modules.catalog.domain.product.aggregate import ProductKind, Product
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import (
    InvalidCatalogValueError,
    CatalogConflictError,
)


class CatalogClassificationDomainTests(unittest.TestCase):
    """Проверяет бизнес-правила без SQL и транспорта."""

    setUp = support.CatalogVariableDomainTests.setUp

    def test_general_enum_values_do_not_change_variations(self) -> None:
        """Visible и общие значения независимы от осей, default и selection."""
        before = self.product.structure
        axis = before.axes[0]
        values = (
            ProductAttributeValueVO(axis.attribute_id, axis.option_ids[0], False, 7),
        )
        definitions = (
            EnumAttributeSnapshot(axis.attribute_id, frozenset(axis.option_ids)),
        )
        self.product.set_attributes(values, definitions, self.actor, self.now)
        self.assertIs(self.product.structure, before)
        self.assertEqual(self.product.attribute_values, values)
        revision = self.product.revision
        for invalid in [
            (values[0], values[0]),
            (replace(values[0], option_id=type(values[0].option_id)(uuid4())),),
        ]:
            with self.assertRaises(InvalidCatalogValueError):
                self.product.set_attributes(invalid, definitions, self.actor, self.now)
        self.assertEqual(self.product.revision, revision)
        self.assertEqual(self.product.attribute_values, values)

    def test_categories_require_one_explicit_primary(self) -> None:
        """Пустой набор очищается; дубликаты, чужая primary и отсутствующие ссылки отвергаются."""
        a, b = CategoryIdVO(uuid4()), CategoryIdVO(uuid4())
        self.product.set_categories((a, b), b, frozenset({a, b}), self.actor, self.now)
        for ids, primary, existing in [
            ((a, a), a, frozenset({a})),
            ((a,), None, frozenset({a})),
            ((a,), b, frozenset({a, b})),
            ((), a, frozenset({a})),
            ((a,), a, frozenset()),
        ]:
            with self.assertRaises(InvalidCatalogValueError):
                self.product.set_categories(
                    ids, primary, existing, self.actor, self.now
                )
        self.assertEqual(self.product.category_ids, (a, b))
        self.product.set_categories((), None, frozenset(), self.actor, self.now)
        self.assertEqual(self.product.category_ids, ())
        self.assertIsNone(self.product.primary_category_id)

    def test_tag_assignments_are_unique_and_preserved(self) -> None:
        """Назначения сохраняются при смене kind и ProductType."""
        tag = TagIdVO(uuid4())
        self.product.set_tags((tag,), frozenset({tag}), self.actor, self.now)
        with self.assertRaises(InvalidCatalogValueError):
            self.product.set_tags((tag, tag), frozenset({tag}), self.actor, self.now)
        with self.assertRaises(InvalidCatalogValueError):
            self.product.set_tags(
                (TagIdVO(uuid4()),), frozenset({tag}), self.actor, self.now
            )
        variant = Variant.create(self.product.variants[0].id, False)
        self.product.change_kind(
            ProductKind.SIMPLE,
            SimpleProductStructure.create(variant),
            (),
            self.schema,
            self.actor,
            self.now,
        )
        self.product.change_type(self.schema, self.actor, self.now)
        self.assertEqual(self.product.tag_ids, (tag,))

    def test_category_cycles_and_used_deletion_are_rejected(self) -> None:
        """Домен запрещает перемещение в себя и под потомка без смены ревизии."""
        a, b = CategoryIdVO(uuid4()), CategoryIdVO(uuid4())
        category = Category.create(
            a, None, frozenset(), LocaleVO("en"), "Root", self.actor, self.now
        )
        for parent, path in [(a, frozenset({a})), (b, frozenset({a, b}))]:
            with self.assertRaises(InvalidCatalogValueError):
                category.move(parent, path, self.actor, self.now)
        self.assertEqual(category.revision, 1)
        with self.assertRaises(CatalogConflictError):
            category.ensure_deletable(True)
        category.move(b, frozenset({b}), self.actor, self.now)
        self.assertEqual(category.parent_id, b)
        category.put_translation(LocaleVO("ru"), "Категория", self.actor, self.now)
        self.assertEqual(category.translations["en"], "Root")

    def test_tag_locales_and_revision(self) -> None:
        """Tag имеет стабильный UUID и отдельные подписи каждой locale."""
        tag = Tag.create(TagIdVO(uuid4()), LocaleVO("en"), "Sale", self.actor, self.now)
        identifier = tag.id
        tag.put_translation(LocaleVO("ru"), "Акция", self.actor, self.now)
        self.assertEqual(tag.translations, {"en": "Sale", "ru": "Акция"})
        self.assertEqual(tag.id, identifier)
        with self.assertRaises(CatalogConflictError):
            tag.ensure_revision(1)
        with self.assertRaises(CatalogConflictError):
            tag.ensure_deletable(True)

    def test_restore_does_not_hide_invalid_primary_rows(self) -> None:
        """Restore получает сырые primary IDs и отклоняет два флага основной категории."""
        a, b = CategoryIdVO(uuid4()), CategoryIdVO(uuid4())
        fields = dict(
            identifier=self.product.id,
            kind=self.product.kind,
            product_type_id=self.product.product_type_id,
            structure=self.product.structure,
            translations={},
            revision=1,
            created_at=self.now,
            updated_at=self.now,
            created_by=self.actor,
            updated_by=self.actor,
            category_ids=(a, b),
        )
        for primary in [(), (a, b)]:
            with self.assertRaises(InvalidCatalogValueError):
                Product.restore(**fields, primary_category_ids=primary)
        self.assertEqual(
            Product.restore(**fields, primary_category_ids=(a,)).primary_category_id, a
        )
