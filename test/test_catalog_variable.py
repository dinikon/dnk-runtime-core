"""Инварианты единой модели CatalogItem, наследования и переходов."""

import unittest
from datetime import datetime, UTC, timedelta
from decimal import Decimal
from dataclasses import replace
from decimal import localcontext
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    WeightVO,
    WeightUnit,
    LengthVO,
    LengthUnit,
    DimensionsVO,
)
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
        with self.assertRaises(InvalidCatalogValueError):
            self.root.set_virtual(self.root.id, True, self.actor, self.now)
        self.root.set_virtual(self.child, False, self.actor, self.now)
        self.root.set_measurements(
            self.child,
            WeightVO(Decimal("0"), WeightUnit.G),
            None,
            self.actor,
            self.now,
        )
        self.assertFalse(self.effective().virtual)
        self.assertEqual(self.effective().weight.value, Decimal("0"))
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
        self.root.set_price(self.root.children[1].id, price, self.actor, self.now)
        before = self.root.revision
        with self.assertRaises(InvalidCatalogValueError):
            self.root.set_price(
                self.child,
                PriceSpecificationVO(Decimal("3"), "USD"),
                self.actor,
                self.now,
            )
        self.assertEqual(self.root.revision, before)
        for value in ["NaN", "Infinity", "-1", "0.0000001"]:
            with self.assertRaises(InvalidCatalogValueError):
                PriceSpecificationVO(Decimal(value), "UAH")

    def test_shared_stock_no_local_copy_and_revisions(self) -> None:
        self.assertEqual(
            self.effective().stock.effective_status(), StockStatus.IN_STOCK
        )
        with self.assertRaises(InvalidCatalogValueError):
            StockSpecificationVO("parent")
        self.root.set_stock(
            self.root.id,
            StockSpecificationVO(True, 0, None, BackorderPolicy.NOTIFY),
            self.actor,
            self.now,
        )
        revision = self.root.revision
        self.root.set_stock(
            self.child,
            StockSpecificationVO(),
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

    def test_measurements_inherit_each_pair_and_keep_zero(self) -> None:
        """Компоненты наследуют родителя независимо и сохраняют собственный ноль."""
        self.root.set_measurements(
            self.root.id,
            WeightVO(Decimal("1.5"), WeightUnit.KG),
            DimensionsVO(
                LengthVO(Decimal("0.8"), LengthUnit.M),
                LengthVO(Decimal("40"), LengthUnit.CM),
                LengthVO(Decimal("20"), LengthUnit.CM),
            ),
            self.actor,
            self.now,
        )
        self.root.set_measurements(
            self.child,
            WeightVO(Decimal("0"), WeightUnit.G),
            DimensionsVO(width=LengthVO(Decimal("0"), LengthUnit.M)),
            self.actor,
            self.now,
        )
        effective = self.effective()
        self.assertEqual(effective.weight, WeightVO(Decimal("0"), WeightUnit.G))
        self.assertEqual(
            effective.dimensions.length, LengthVO(Decimal("0.8"), LengthUnit.M)
        )
        self.assertEqual(
            effective.dimensions.width, LengthVO(Decimal("0"), LengthUnit.M)
        )
        self.assertEqual(effective.origins["dimensions.length"].source, "parent")
        self.assertEqual(effective.origins["dimensions.width"].source, "item")
        self.root.set_measurements(self.child, None, None, self.actor, self.now)
        self.assertEqual(self.effective().weight.in_grams(), Decimal("1500"))
        self.assertEqual(
            self.effective().dimensions.length.in_millimeters(), Decimal("800")
        )
        self.root.set_measurements(self.root.id, None, None, self.actor, self.now)
        self.assertIsNone(self.effective().weight)
        self.assertIsNone(self.effective().dimensions)

    def test_measurement_precision_units_and_exact_conversion(self) -> None:
        """Точность считается в канонических единицах и не зависит от Decimal context."""
        for unit, value, expected in [
            (WeightUnit.G, "0.000001", "0.000001"),
            (WeightUnit.KG, "0.000000001", "0.000001"),
        ]:
            self.assertEqual(
                WeightVO(Decimal(value), unit).in_grams(), Decimal(expected)
            )
        for unit, value in [
            (LengthUnit.CM, "0.0000001"),
            (LengthUnit.M, "0.000000001"),
        ]:
            self.assertEqual(
                LengthVO(Decimal(value), unit).in_millimeters(), Decimal("0.000001")
            )
        with localcontext() as context:
            context.prec = 5
            result = WeightVO(
                Decimal("123456789012345678901234567890.123456789"), WeightUnit.KG
            ).in_grams()
            self.assertEqual(str(result), "123456789012345678901234567890123.456789")
        for value in ["NaN", "Infinity", "-1", "0.0000000001"]:
            with self.subTest(value=value), self.assertRaises(InvalidCatalogValueError):
                WeightVO(Decimal(value), WeightUnit.KG)
        for factory in [
            lambda: WeightVO(Decimal("1"), "kg"),
            lambda: LengthVO(Decimal("1"), WeightUnit.G),
            lambda: DimensionsVO(Decimal("1")),
        ]:
            with self.assertRaises(InvalidCatalogValueError):
                factory()

    def test_stock_manual_signed_quantity_and_independent_child(self) -> None:
        """Отрицательный запас разрешён, а собственный учёт перекрывает общий."""
        for policy in BackorderPolicy:
            value = StockSpecificationVO(True, -3, None, policy)
            self.assertEqual(
                value.effective_status(),
                (
                    StockStatus.OUT_OF_STOCK
                    if policy == BackorderPolicy.NO
                    else StockStatus.ON_BACKORDER
                ),
            )
        self.root.set_stock(
            self.root.id, StockSpecificationVO(True, 10, None), self.actor, self.now
        )
        self.root.set_stock(
            self.child, StockSpecificationVO(True, -1, None), self.actor, self.now
        )
        self.assertEqual(self.effective().stock_source_id, self.child)
        self.assertEqual(
            self.effective().stock.effective_status(), StockStatus.OUT_OF_STOCK
        )
        self.root.set_stock(self.child, StockSpecificationVO(), self.actor, self.now)
        self.assertEqual(self.effective().stock_source_id, self.root.id)
        self.assertEqual(self.effective().stock.stock_quantity, 10)
        self.root.set_stock(self.root.id, StockSpecificationVO(), self.actor, self.now)
        self.assertEqual(self.effective().stock_source_id, self.child)
        self.assertIsNone(self.effective().stock.stock_quantity)
        manual = StockSpecificationVO(False, None, StockStatus.ON_BACKORDER)
        self.assertEqual(manual.effective_status(), StockStatus.ON_BACKORDER)
        for factory in [
            lambda: StockSpecificationVO(True),
            lambda: StockSpecificationVO(True, True, None),
            lambda: StockSpecificationVO(False, 1),
            lambda: StockSpecificationVO(
                False, None, StockStatus.IN_STOCK, BackorderPolicy.YES
            ),
        ]:
            with self.assertRaises(InvalidCatalogValueError):
                factory()

    def test_sale_availability_and_family_summary(self) -> None:
        """Продажа требует активной семьи, цены и наличия; сводка не суммирует запас."""
        self.root.set_price(
            self.child, PriceSpecificationVO(Decimal("0"), "UAH"), self.actor, self.now
        )
        self.root.set_status(self.child, CatalogItemStatus.ACTIVE, self.actor, self.now)
        self.assertFalse(self.effective().available_for_sale)
        self.root.set_status(
            self.root.id, CatalogItemStatus.ACTIVE, self.actor, self.now
        )
        self.assertTrue(self.effective().available_for_sale)
        self.root.set_stock(
            self.root.id, StockSpecificationVO(True, 0, None), self.actor, self.now
        )
        self.assertFalse(self.effective().available_for_sale)
        self.root.set_stock(
            self.root.id,
            StockSpecificationVO(True, -2, None, BackorderPolicy.YES),
            self.actor,
            self.now,
        )
        self.assertTrue(self.effective().available_for_sale)
        self.root.set_status(
            self.root.children[1].id, CatalogItemStatus.ACTIVE, self.actor, self.now
        )
        children = tuple(
            CatalogItemEffectiveValuesPolicy.resolve(
                c.snapshot(), self.root.snapshot(), "en", self.now
            )
            for c in self.root.children
        )
        summary = CatalogItemEffectiveValuesPolicy.family_summary(
            self.root.snapshot(), children
        )
        self.assertTrue(summary.available_for_sale)
        self.assertTrue(summary.price_incomplete)
        self.assertEqual(summary.price_min, 0)
        self.assertEqual(summary.stock_status, StockStatus.ON_BACKORDER)
        self.root.set_stock(
            self.root.children[1].id,
            StockSpecificationVO(True, 5, None),
            self.actor,
            self.now,
        )
        self.root.set_stock(
            self.child, StockSpecificationVO(True, 0, None), self.actor, self.now
        )
        children = tuple(
            CatalogItemEffectiveValuesPolicy.resolve(
                c.snapshot(), self.root.snapshot(), "en", self.now
            )
            for c in self.root.children
        )
        summary = CatalogItemEffectiveValuesPolicy.family_summary(
            self.root.snapshot(), children
        )
        self.assertEqual(summary.stock_status, StockStatus.IN_STOCK)
        self.assertFalse(summary.available_for_sale)
        self.root.set_status(
            self.root.id, CatalogItemStatus.ARCHIVED, self.actor, self.now
        )
        children = tuple(
            CatalogItemEffectiveValuesPolicy.resolve(
                c.snapshot(), self.root.snapshot(), "en", self.now
            )
            for c in self.root.children
        )
        summary = CatalogItemEffectiveValuesPolicy.family_summary(
            self.root.snapshot(), children
        )
        self.assertFalse(summary.available_for_sale)
        self.assertEqual(summary.stock_status, StockStatus.OUT_OF_STOCK)

    def test_kind_transitions_keep_units_and_materialize_shared_stock(self) -> None:
        """Переходы явно переносят коммерческие значения и материализуют измерения."""
        self.simple.set_price(
            self.simple.id,
            PriceSpecificationVO(Decimal("5"), "UAH"),
            self.actor,
            self.now,
        )
        self.simple.set_virtual(self.simple.id, True, self.actor, self.now)
        self.simple.set_stock(
            self.simple.id, StockSpecificationVO(True, 7, None), self.actor, self.now
        )
        self.simple.set_measurements(
            self.simple.id,
            WeightVO(Decimal("2"), WeightUnit.KG),
            DimensionsVO(height=LengthVO(Decimal("0.3"), LengthUnit.M)),
            self.actor,
            self.now,
        )
        children = tuple(
            CatalogItem.create_variant(
                CatalogItemIdVO(uuid4()),
                self.simple.id,
                VariationSelectionVO(((self.attribute, o),)),
                self.actor,
                self.now,
            )
            for o in self.options
        )
        with self.assertRaises(InvalidCatalogValueError):
            self.simple.change_to_variable(
                (self.axis,),
                children,
                None,
                self.definitions,
                None,
                False,
                self.actor,
                self.now,
            )
        self.simple.change_to_variable(
            (self.axis,),
            children,
            None,
            self.definitions,
            children[0].id,
            False,
            self.actor,
            self.now,
        )
        self.assertIsNone(self.simple.price)
        self.assertFalse(self.simple.virtual)
        self.assertFalse(self.simple.stock.manage_stock)
        self.assertEqual(self.simple.children[0].price.regular_price, 5)
        self.assertIsNone(self.simple.children[1].price)
        self.assertTrue(self.simple.children[0].virtual)
        self.assertIsNone(self.simple.children[0].weight)
        self.simple.set_stock(
            self.simple.id, StockSpecificationVO(True, 11, None), self.actor, self.now
        )
        selected = self.simple.children[1].id
        self.simple.change_to_simple(
            selected,
            frozenset(c.id for c in self.simple.children),
            False,
            self.actor,
            self.now,
        )
        self.assertEqual(self.simple.weight, WeightVO(Decimal("2"), WeightUnit.KG))
        self.assertEqual(
            self.simple.dimensions.height, LengthVO(Decimal("0.3"), LengthUnit.M)
        )
        self.assertTrue(self.simple.stock.manage_stock)
        self.assertEqual(self.simple.stock.stock_quantity, 11)
        self.assertEqual(self.simple.children, ())
