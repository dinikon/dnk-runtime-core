"""Идентичность атрибутов и опций, переводы и HTTP-контракты без кодов."""

import unittest
from datetime import UTC, datetime
from uuid import uuid4

from pydantic import ValidationError

from src.modules.catalog.domain.attribute.aggregate import AttributeDefinition
from src.modules.catalog.domain.attribute.entity.option import AttributeOption
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.presentation.attribute.http.request.create_attribute import (
    CreateAttributeRequest,
)
from src.modules.catalog.presentation.attribute.http.request.replace_attribute_options import (
    ReplaceAttributeOptionsRequest,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CatalogAttributeIdentityTests(unittest.TestCase):
    """Проверяет доменные правила независимо от SQL и HTTP-обработчиков."""

    def setUp(self) -> None:
        """Создаёт атрибут с двумя самостоятельными опциями без кодов."""
        self.actor = EntityIdVO(uuid4())
        self.now = datetime.now(UTC)
        self.red = AttributeOption.create(
            AttributeOptionIdVO(uuid4()), LocaleVO("en"), "Red"
        )
        self.blue = AttributeOption.create(
            AttributeOptionIdVO(uuid4()), LocaleVO("en"), "Blue"
        )
        self.attribute = AttributeDefinition.create(
            AttributeIdVO(uuid4()),
            LocaleVO("en"),
            "Color",
            (self.red, self.blue),
            self.actor,
            self.now,
        )

    def test_translation_and_order_preserve_ids_and_other_locales(self) -> None:
        """Переименование и сортировка сохраняют UUID, английский и русский переводы."""
        identifier = self.attribute.id
        translated = self.red.translated(LocaleVO("ru"), "Красный")
        self.attribute.put_translation(LocaleVO("ru"), "Цвет", self.actor, self.now)
        self.attribute.replace_options(
            (self.blue, translated), frozenset(), self.actor, self.now
        )
        self.assertEqual(self.attribute.id, identifier)
        self.assertEqual(self.attribute.translations, {"en": "Color", "ru": "Цвет"})
        self.assertEqual(
            tuple(o.id for o in self.attribute.options), (self.blue.id, self.red.id)
        )
        self.assertEqual(translated.translations, {"en": "Red", "ru": "Красный"})
        self.assertFalse(hasattr(self.attribute, "code"))
        self.assertFalse(hasattr(translated, "code"))

    def test_missing_translation_is_preserved_while_reordering(self) -> None:
        """None не создаёт пустой перевод при структурном изменении списка."""
        blue = self.blue.translated(LocaleVO("ru"), None)
        self.attribute.replace_options(
            (blue, self.red), frozenset(), self.actor, self.now
        )
        self.assertEqual(blue.translations, {"en": "Blue"})
        for invalid in (None, "", "   "):
            with self.assertRaises(InvalidCatalogValueError):
                AttributeOption.create(
                    AttributeOptionIdVO(uuid4()), LocaleVO("ru"), invalid
                )

    def test_labels_do_not_define_identity_but_option_ids_are_unique(self) -> None:
        """Совпадающие подписи допустимы; повтор одного UUID отклоняется атомарно."""
        duplicate_label = self.blue.translated(LocaleVO("en"), "Red")
        self.attribute.replace_options(
            (self.red, duplicate_label), frozenset(), self.actor, self.now
        )
        before = self.attribute.options
        with self.assertRaises(InvalidCatalogValueError):
            self.attribute.replace_options(
                (self.red, self.red), frozenset(), self.actor, self.now
            )
        self.assertEqual(self.attribute.options, before)

    def test_used_option_and_foreign_option_are_rejected(self) -> None:
        """ID защищает принадлежность и удаление независимо от названия."""
        with self.assertRaises(CatalogConflictError):
            self.attribute.replace_options(
                (self.blue,), frozenset({self.red.id}), self.actor, self.now
            )
        self.assertEqual(self.attribute.options, (self.red, self.blue))
        with self.assertRaises(InvalidCatalogValueError):
            self.attribute.get_option(AttributeOptionIdVO(uuid4()))
        with self.assertRaises(CatalogConflictError):
            self.attribute.ensure_deletable(True)

    def test_request_contracts_accept_labels_and_reject_codes(self) -> None:
        """Создание не требует кодов и отклоняет прежние поля без aliases."""
        body = {"locale": "en", "label": "Color", "options": [{"label": "Blue"}]}
        self.assertEqual(
            CreateAttributeRequest.model_validate(body).options[0].label, "Blue"
        )
        for invalid in (
            {**body, "code": "color"},
            {**body, "options": [{"code": "blue", "label": "Blue"}]},
        ):
            with self.assertRaises(ValidationError):
                CreateAttributeRequest.model_validate(invalid)
        request = ReplaceAttributeOptionsRequest.model_validate(
            {
                "options": [
                    {"option_id": str(self.red.id)},
                    {"option_id": str(self.blue.id), "label": None},
                ]
            }
        )
        self.assertTrue(all(o.label is None for o in request.options))
        with self.assertRaises(ValidationError):
            ReplaceAttributeOptionsRequest.model_validate(
                {"options": [{"label": "Blue", "code": "blue"}]}
            )
