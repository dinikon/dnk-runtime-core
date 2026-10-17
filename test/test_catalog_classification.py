import unittest
from uuid import uuid4
from datetime import datetime, UTC
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.category.aggregate import Category
from src.modules.catalog.domain.category.value_object.identifier import CategoryIdVO
from src.modules.catalog.domain.tag.aggregate import Tag
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import (
    InvalidCatalogValueError,
    CatalogConflictError,
)


class CatalogClassificationDomainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.actor = EntityIdVO(uuid4())
        self.now = datetime.now(UTC)

    def test_category_cycles_and_used_deletion_are_rejected(self) -> None:
        """Домен запрещает перемещение в себя и под потомка без смены ревизии."""
        a, b = CategoryIdVO(uuid4()), CategoryIdVO(uuid4())
        category = Category.create(
            a, None, frozenset(), LocaleVO("en"), "Root", self.actor, self.now
        )
        for parent, path in [(a, frozenset({a})), (b, frozenset({a, b}))]:
            with self.assertRaises(InvalidCatalogValueError):
                category.move(parent, path, self.actor, self.now)
        self.assertFalse(hasattr(category, "revision"))
        with self.assertRaises(CatalogConflictError):
            category.ensure_deletable(True)
        category.move(b, frozenset({b}), self.actor, self.now)
        self.assertEqual(category.parent_id, b)
        category.put_translation(LocaleVO("ru"), "Категория", self.actor, self.now)
        self.assertEqual(category.translations["en"], "Root")

    def test_tag_locales_without_revision(self) -> None:
        """Tag имеет стабильный UUID и отдельные подписи каждой locale."""
        tag = Tag.create(TagIdVO(uuid4()), LocaleVO("en"), "Sale", self.actor, self.now)
        identifier = tag.id
        tag.put_translation(LocaleVO("ru"), "Акция", self.actor, self.now)
        self.assertEqual(tag.translations, {"en": "Sale", "ru": "Акция"})
        self.assertEqual(tag.id, identifier)
        self.assertFalse(hasattr(tag, "revision"))
        with self.assertRaises(CatalogConflictError):
            tag.ensure_deletable(True)
