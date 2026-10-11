"""Инварианты единой модели CatalogItem, наследования и переходов."""

import unittest
from datetime import datetime, UTC, timedelta
from decimal import Decimal
from dataclasses import replace
from uuid import uuid4
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.kind import (
    CatalogItemKind,
    CatalogItemStatus,
)
from src.modules.catalog.domain.catalog_item.value_object.override import (
    OverrideVO,
    OverrideMode,
)
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
    StockManagement,
    StockStatus,
    BackorderPolicy,
)
from src.modules.catalog.domain.catalog_item.value_object.axis import VariationAxis
from src.modules.catalog.domain.catalog_item.value_object.selection import (
    VariationSelectionVO,
)
from src.modules.catalog.domain.catalog_item.value_object.attribute_snapshot import (
    EnumAttributeSnapshot,
)
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.catalog.domain.catalog_item.entity.image import CatalogItemImage
from src.modules.catalog.domain.catalog_item.entity.metadata import CatalogMetadataEntry
from src.modules.catalog.domain.catalog_item.policy.effective_values import (
    CatalogItemEffectiveValuesPolicy,
)
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.product_type.value_object.schema import (
    ProductTypeSchemaSnapshot,
    DEFAULT_TYPE_ID,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import (
    InvalidCatalogValueError,
    CatalogConflictError,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CatalogItemDomainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 10, 11, tzinfo=UTC)
        self.actor = EntityIdVO(uuid4())
        self.simple = CatalogItem.create_simple(
            CatalogItemIdVO(uuid4()), self.actor, self.now
        )
        self.attribute = AttributeIdVO(uuid4())
        self.options = tuple(AttributeOptionIdVO(uuid4()) for _ in range(2))
        self.axis = VariationAxis(self.attribute, self.options, 0, False)
        self.definitions = (
            EnumAttributeSnapshot(self.attribute, frozenset(self.options)),
        )
        root_id = CatalogItemIdVO(uuid4())
        children = tuple(
            CatalogItem.create_variant(
                CatalogItemIdVO(uuid4()),
                root_id,
                VariationSelectionVO(((self.attribute, o),)),
                self.actor,
                self.now,
            )
            for o in self.options
        )
        self.root = CatalogItem.create_variable(
            root_id,
            (self.axis,),
            children,
            children[0].selection,
            self.definitions,
            self.actor,
            self.now,
        )
        self.child = self.root.children[0].id
        self.schema = ProductTypeSchemaSnapshot(DEFAULT_TYPE_ID, "default", 1, ())

    def effective(self) -> object:
        return CatalogItemEffectiveValuesPolicy.resolve(
            self.root.find_item(self.child).snapshot(),
            self.root.snapshot(),
            "en",
            self.now,
        )

    def test_one_model_and_simple_has_no_hidden_variant(self) -> None:
        self.assertEqual(self.simple.children, ())
        self.assertTrue(all(type(c) is CatalogItem for c in self.root.children))
        self.assertEqual(self.root.find_item(self.child).parent_id, self.root.id)

    def test_gallery_ids_and_materialized_attribute_order(self) -> None:
        """Image ID уникален во всей семье; позиции разных наборов нормализуются при переходе."""
        image = CatalogItemImage.create(EntityIdVO(uuid4()), EntityIdVO(uuid4()), 0)
        gallery = CatalogItemGallery.create((image,), image.id)
        self.root.replace_gallery(
            self.root.id, LocaleVO("en"), gallery, self.actor, self.now
        )
        with self.assertRaises(InvalidCatalogValueError):
            self.root.replace_gallery(
                self.child, LocaleVO("ru"), gallery, self.actor, self.now
            )
        from src.modules.catalog.domain.catalog_item.value_object.attribute import (
            EnumAttributeAssignmentVO,
        )

        extra = AttributeIdVO(uuid4())
        option = AttributeOptionIdVO(uuid4())
        self.root.set_attributes(
            self.root.id,
            (EnumAttributeAssignmentVO(extra, (option,), True, 0),),
            (EnumAttributeSnapshot(extra, frozenset({option})),),
            self.actor,
            self.now,
        )
        self.root.change_to_simple(
            self.child,
            frozenset(c.id for c in self.root.children),
            False,
            self.actor,
            self.now,
        )
        self.assertEqual([a.position for a in self.root.attributes], [0, 1])

    def test_content_same_locale_clear_false_zero(self) -> None:
        self.root.put_content(
            self.root.id,
            LocaleVO("en"),
            {
                "name": OverrideVO(OverrideMode.SET, "Parent"),
                "desc": OverrideVO(OverrideMode.SET, "Text"),
            },
            self.schema,
            1,
            self.actor,
            self.now,
        )
        self.root.put_content(
            self.child,
            LocaleVO("en"),
            {
                "desc": OverrideVO(OverrideMode.CLEAR),
                "short_desc": OverrideVO(OverrideMode.SET, ""),
            },
            self.schema,
            1,
            self.actor,
            self.now,
        )
        self.assertEqual(self.effective().content, {"name": "Parent", "short_desc": ""})
        self.root.set_virtual(
            self.root.id, OverrideVO(OverrideMode.SET, True), self.actor, self.now
        )
        self.root.set_virtual(
            self.child, OverrideVO(OverrideMode.SET, False), self.actor, self.now
        )
        self.root.set_measurements(
            self.child,
            OverrideVO(OverrideMode.SET, Decimal("0")),
            OverrideVO(OverrideMode.CLEAR),
            self.actor,
            self.now,
        )
        self.assertFalse(self.effective().virtual)
        self.assertEqual(self.effective().weight, Decimal("0"))
        self.assertIsNone(
            CatalogItemEffectiveValuesPolicy.resolve(
                self.root.find_item(self.child).snapshot(),
                self.root.snapshot(),
                "ru",
                self.now,
            ).content
        )

    def test_price_boundaries_precision_and_single_currency(self) -> None:
        price = PriceSpecificationVO(
            Decimal("10"), "UAH", Decimal("0"), self.now, self.now + timedelta(hours=1)
        )
        self.assertEqual(price.at(self.now), 0)
        self.assertEqual(price.at(self.now + timedelta(hours=1)), 10)
        self.root.set_price(
            self.root.id, OverrideVO(OverrideMode.SET, price), self.actor, self.now
        )
        before = self.root.revision
        with self.assertRaises(InvalidCatalogValueError):
            self.root.set_price(
                self.child,
                OverrideVO(OverrideMode.SET, PriceSpecificationVO(Decimal("3"), "USD")),
                self.actor,
                self.now,
            )
        self.assertEqual(self.root.revision, before)
        for value in ["NaN", "Infinity", "-1", "0.0000001"]:
            with self.assertRaises(InvalidCatalogValueError):
                PriceSpecificationVO(Decimal(value), "UAH")

    def test_shared_stock_no_local_copy_and_revisions(self) -> None:
        with self.assertRaises(InvalidCatalogValueError):
            self.root.set_stock(
                self.child,
                StockSpecificationVO(StockManagement.PARENT),
                self.actor,
                self.now,
            )
        self.root.set_stock(
            self.root.id,
            StockSpecificationVO(StockManagement.OWN, 0, None, BackorderPolicy.NOTIFY),
            self.actor,
            self.now,
        )
        revision = self.root.revision
        self.root.set_stock(
            self.child,
            StockSpecificationVO(StockManagement.PARENT),
            self.actor,
            self.now,
        )
        self.assertEqual(self.effective().stock_source_id, self.root.id)
        self.assertEqual(
            self.effective().stock.effective_status(), StockStatus.ON_BACKORDER
        )
        self.assertIsNone(self.root.find_item(self.child).stock.stock_quantity)
        self.assertEqual(self.root.revision, revision + 1)
        self.assertEqual(self.root.children[1].revision, 1)
        with self.assertRaises(CatalogConflictError):
            self.root.ensure_revision(revision)

    def test_gallery_whole_set_empty_and_inherit(self) -> None:
        image = CatalogItemImage.create(
            EntityIdVO(uuid4()), EntityIdVO(uuid4()), 0, "alt", "caption"
        )
        self.root.replace_gallery(
            self.root.id,
            LocaleVO("en"),
            CatalogItemGallery.create((image,), image.id),
            self.actor,
            self.now,
        )
        self.assertEqual(self.effective().gallery.images, (image,))
        self.root.replace_gallery(
            self.child,
            LocaleVO("en"),
            CatalogItemGallery.create((), None),
            self.actor,
            self.now,
        )
        self.assertEqual(self.effective().gallery.images, ())
        self.root.delete_gallery(self.child, LocaleVO("en"), self.actor, self.now)
        self.assertEqual(self.effective().gallery.images, (image,))
        with self.assertRaises(InvalidCatalogValueError):
            self.root.replace_gallery(
                self.root.id,
                LocaleVO("en"),
                CatalogItemGallery.create((image,), EntityIdVO(uuid4())),
                self.actor,
                self.now,
            )

    def test_metadata_order_clear_and_reserved_keys(self) -> None:
        parent = (
            CatalogMetadataEntry.create("a", "text", "A", 0, OverrideMode.SET),
            CatalogMetadataEntry.create("b", "boolean", False, 1, OverrideMode.SET),
        )
        child = (
            CatalogMetadataEntry.create("a", "text", "override", 1, OverrideMode.SET),
            CatalogMetadataEntry.create(
                "c", "decimal", Decimal("0"), 0, OverrideMode.SET
            ),
        )
        self.root.set_metadata(self.root.id, parent, self.actor, self.now)
        self.root.set_metadata(self.child, child, self.actor, self.now)
        self.assertEqual([v.key for v in self.effective().metadata], ["a", "b", "c"])
        with self.assertRaises(InvalidCatalogValueError):
            self.root.set_metadata(
                self.child,
                (
                    CatalogMetadataEntry.create(
                        "price", "text", "1", 0, OverrideMode.SET
                    ),
                ),
                self.actor,
                self.now,
            )

    def test_structure_and_transition_materialize_effective(self) -> None:
        with self.assertRaises(InvalidCatalogValueError):
            CatalogItem.create_variable(
                self.root.id,
                (self.axis,),
                self.root.children[:1],
                None,
                self.definitions,
                self.actor,
                self.now,
            )
        root_id = self.root.id
        self.root.put_content(
            root_id,
            LocaleVO("en"),
            {"name": OverrideVO(OverrideMode.SET, "Parent")},
            self.schema,
            1,
            self.actor,
            self.now,
        )
        self.root.change_to_simple(
            self.child,
            frozenset(c.id for c in self.root.children),
            False,
            self.actor,
            self.now,
        )
        self.assertEqual(self.root.id, root_id)
        self.assertEqual(self.root.kind, CatalogItemKind.SIMPLE)
        self.assertEqual(self.root.translations["en"]["name"].value, "Parent")
        self.assertEqual(self.root.children, ())
