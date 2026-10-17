"""Регрессия самостоятельных товаров без наследования и вариативных сценариев."""

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
import unittest
from uuid import uuid4
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.catalog.domain.catalog_item.entity.image import CatalogItemImage
from src.modules.catalog.domain.catalog_item.entity.metadata import CatalogMetadataEntry
from src.modules.catalog.domain.catalog_item.policy.values import (
    CatalogItemValuesPolicy,
)
from src.modules.catalog.domain.catalog_item.value_object.attribute import (
    EnumAttributeAssignmentVO,
)
from src.modules.catalog.domain.catalog_item.value_object.attribute_snapshot import (
    EnumAttributeSnapshot,
)
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    WeightVO,
    WeightUnit,
    LengthVO,
    LengthUnit,
    DimensionsVO,
)
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.sku import SkuCodeVO
from src.modules.catalog.domain.catalog_item.value_object.status import (
    CatalogItemStatus,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
    StockStatus,
    BackorderPolicy,
)
from src.modules.catalog.domain.attribute.value_object.identifier import AttributeIdVO
from src.modules.catalog.domain.attribute.value_object.option_id import (
    AttributeOptionIdVO,
)
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)
from src.modules.catalog.domain.product_type.value_object.schema import (
    DEFAULT_TYPE_ID,
    ProductTypeSchemaSnapshot,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.infrastructure.catalog_item.persistence.mapper import (
    CatalogItemMapper,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.query_mapper import (
    CatalogItemQueryMapper,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class CatalogSimpleDomainTests(unittest.TestCase):
    """Проверяет инварианты товара, чистые вычисления и сохранение собственных значений."""

    def setUp(self) -> None:
        """Создаёт товар и независимые снимки справочников."""
        self.now = datetime(2026, 10, 17, tzinfo=UTC)
        self.actor = EntityIdVO(uuid4())
        self.item = CatalogItem.create(CatalogItemIdVO(uuid4()), self.actor, self.now)
        self.schema = ProductTypeSchemaSnapshot(DEFAULT_TYPE_ID, "default", 1, ())
        self.attribute = AttributeIdVO(uuid4())
        self.options = (AttributeOptionIdVO(uuid4()), AttributeOptionIdVO(uuid4()))
        self.definitions = (
            EnumAttributeSnapshot(self.attribute, frozenset(self.options)),
        )

    def test_creation_and_restore_validate_one_item(self) -> None:
        """Создание не содержит семейных полей, восстановление проверяет инварианты."""
        self.assertFalse(hasattr(self.item, "revision"))
        self.assertEqual(self.item.product_type_id, DEFAULT_TYPE_ID)
        self.assertFalse(self.item.stock.manage_stock)
        self.assertEqual(self.item.stock.effective_status(), StockStatus.IN_STOCK)
        self.assertFalse(
            {"kind", "parent_id", "children", "axes", "selection"}
            & {f.name for f in fields(self.item)}
        )
        values = {f.name: getattr(self.item, f.name) for f in fields(self.item)}
        values["identifier"] = values.pop("id")
        restored = CatalogItem.restore(**values)
        self.assertEqual(restored.snapshot(), self.item.snapshot())
        for changes in (
            {"product_type_id": EntityIdVO(uuid4())},
            {"created_at": self.now.replace(tzinfo=None)},
            {"virtual": "false"},
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidCatalogValueError),
            ):
                CatalogItem.restore(**{**values, **changes})

    def test_update_and_failed_change_are_atomic(self) -> None:
        """Ошибка сохраняет прежнее состояние, успешный метод принимает итоговое состояние."""
        before = self.item.snapshot()
        with self.assertRaises(InvalidCatalogValueError):
            self.item.update(
                fields=frozenset({"content"}),
                actor=self.actor,
                now=self.now,
                content={"desc": "No name"},
                locale=LocaleVO("en"),
                schema=self.schema,
                expected_schema_version=1,
            )
        self.assertEqual(self.item.snapshot(), before)
        self.item.update(
            fields=frozenset({"status"}),
            actor=self.actor,
            now=self.now,
            status=CatalogItemStatus.ACTIVE,
        )
        self.assertFalse(hasattr(self.item, "revision"))
        with self.assertRaises(CatalogConflictError):
            self.item.ensure_deletable(True)
        self.item.ensure_deletable(False)

    def test_content_full_replacement_locale_and_empty_text(self) -> None:
        """Переводы независимы, отсутствие удаляет optional блок, пустой текст сохраняется."""
        self.item.update(
            fields=frozenset({"content"}),
            actor=self.actor,
            now=self.now,
            content={"name": "Name", "desc": "", "short_desc": "Short"},
            locale=LocaleVO("en"),
            schema=self.schema,
            expected_schema_version=1,
        )
        self.item.update(
            fields=frozenset({"content"}),
            actor=self.actor,
            now=self.now,
            content={"name": "Имя"},
            locale=LocaleVO("ru"),
            schema=self.schema,
            expected_schema_version=1,
        )
        self.item.update(
            fields=frozenset({"content"}),
            actor=self.actor,
            now=self.now,
            content={"name": "New", "desc": ""},
            locale=LocaleVO("en"),
            schema=self.schema,
            expected_schema_version=1,
        )
        self.assertEqual(self.item.translations["en"], {"name": "New", "desc": ""})
        self.assertEqual(self.item.translations["ru"]["name"], "Имя")
        with self.assertRaises(CatalogConflictError):
            self.item.update(
                fields=frozenset({"content"}),
                actor=self.actor,
                now=self.now,
                content={"name": "Name"},
                locale=LocaleVO("en"),
                schema=self.schema,
                expected_schema_version=2,
            )
        for content in (
            {"name": " "},
            {"name": "x" * 256},
            {"name": "Name", "extra": "x"},
            {"name": {"mode": "set", "value": "Name"}},
        ):
            with (
                self.subTest(content=content),
                self.assertRaises(InvalidCatalogValueError),
            ):
                self.item.update(
                    fields=frozenset({"content"}),
                    actor=self.actor,
                    now=self.now,
                    content=content,
                    locale=LocaleVO("en"),
                    schema=self.schema,
                    expected_schema_version=1,
                )
        self.item.update(
            fields=frozenset({"content"}),
            actor=self.actor,
            now=self.now,
            content=None,
            locale=LocaleVO("en"),
        )
        self.assertNotIn("en", self.item.translations)
        self.assertIn("ru", self.item.translations)

    def test_price_boundaries_and_zero_availability(self) -> None:
        """Скидка действует в интервале [from,to); нулевая цена допускает продажу."""
        price = PriceSpecificationVO(
            Decimal("10"), "UAH", Decimal("0"), self.now, self.now + timedelta(hours=1)
        )
        self.item.update(
            fields=frozenset({"price_specification"}),
            actor=self.actor,
            now=self.now,
            price_specification=price,
        )
        self.item.update(
            fields=frozenset({"status"}),
            actor=self.actor,
            now=self.now,
            status=CatalogItemStatus.ACTIVE,
        )
        for as_of, expected in (
            (self.now - timedelta(microseconds=1), Decimal("10")),
            (self.now, Decimal("0")),
            (self.now + timedelta(hours=1), Decimal("10")),
        ):
            result = CatalogItemValuesPolicy.calculate(self.item.snapshot(), as_of)
            self.assertEqual(result.price, expected)
            self.assertTrue(result.available_for_sale)
        self.item.update(
            fields=frozenset({"price_specification"}),
            actor=self.actor,
            now=self.now,
            price_specification=None,
        )
        self.assertFalse(
            CatalogItemValuesPolicy.calculate(
                self.item.snapshot(), self.now
            ).available_for_sale
        )
        for regular in (Decimal("-1"), Decimal("NaN"), Decimal("0.0000001")):
            with self.assertRaises(InvalidCatalogValueError):
                PriceSpecificationVO(regular, "UAH")

    def test_stock_policies_and_virtuality(self) -> None:
        """Наличие определяется только своим количеством/статусом и не зависит от virtual."""
        self.item.update(
            fields=frozenset({"price_specification"}),
            actor=self.actor,
            now=self.now,
            price_specification=PriceSpecificationVO(Decimal("0"), "UAH"),
        )
        self.item.update(
            fields=frozenset({"status"}),
            actor=self.actor,
            now=self.now,
            status=CatalogItemStatus.ACTIVE,
        )
        for quantity, backorders, status in (
            (1, BackorderPolicy.NO, StockStatus.IN_STOCK),
            (0, BackorderPolicy.NO, StockStatus.OUT_OF_STOCK),
            (-2, BackorderPolicy.NOTIFY, StockStatus.ON_BACKORDER),
            (-1, BackorderPolicy.YES, StockStatus.ON_BACKORDER),
        ):
            self.item.update(
                fields=frozenset({"stock"}),
                actor=self.actor,
                now=self.now,
                stock=StockSpecificationVO(True, quantity, None, backorders),
            )
            result = CatalogItemValuesPolicy.calculate(self.item.snapshot(), self.now)
            self.assertEqual(result.stock_status, status)
            self.assertEqual(
                result.available_for_sale, status != StockStatus.OUT_OF_STOCK
            )
        self.item.update(
            fields=frozenset({"stock"}),
            actor=self.actor,
            now=self.now,
            stock=StockSpecificationVO(
                False, None, StockStatus.ON_BACKORDER, BackorderPolicy.NO
            ),
        )
        self.item.update(
            fields=frozenset({"virtual"}), actor=self.actor, now=self.now, virtual=True
        )
        result = CatalogItemValuesPolicy.calculate(self.item.snapshot(), self.now)
        self.assertTrue(result.backordered)
        self.assertFalse(result.backorders_allowed)
        self.assertTrue(result.available_for_sale)
        for values in (
            ("false", None, StockStatus.IN_STOCK, BackorderPolicy.NO),
            (True, None, None, BackorderPolicy.NO),
            (False, 1, StockStatus.IN_STOCK, BackorderPolicy.NO),
        ):
            with self.assertRaises(InvalidCatalogValueError):
                StockSpecificationVO(*values)

    def test_measurements_precision_units_and_no_inheritance(self) -> None:
        """Размеры сохраняют точные пары; отсутствие и ноль остаются различными."""
        weight = WeightVO(Decimal("0.000000001"), WeightUnit.KG)
        length = LengthVO(Decimal("0.8"), LengthUnit.M)
        self.item.update(
            fields=frozenset({"weight", "dimensions"}),
            actor=self.actor,
            now=self.now,
            weight=weight,
            dimensions=DimensionsVO(
                length, None, LengthVO(Decimal("0"), LengthUnit.CM)
            ),
        )
        self.item.update(
            fields=frozenset({"virtual"}), actor=self.actor, now=self.now, virtual=True
        )
        self.assertEqual(self.item.weight, weight)
        self.assertEqual(self.item.dimensions.length, length)
        self.assertIsNone(self.item.dimensions.width)
        self.assertEqual(self.item.dimensions.height.value, Decimal("0"))
        with self.assertRaises(InvalidCatalogValueError):
            WeightVO(Decimal("0.0000000001"), WeightUnit.KG)
        with self.assertRaises(InvalidCatalogValueError):
            LengthVO(Decimal("-1"), LengthUnit.CM)
        self.item.update(
            fields=frozenset({"weight", "dimensions"}),
            actor=self.actor,
            now=self.now,
            weight=None,
            dimensions=None,
        )
        self.assertIsNone(self.item.weight)
        self.assertIsNone(self.item.dimensions)

    def test_attribute_values_and_classification_invariants(self) -> None:
        """Несколько options не создают варианты; принадлежность и primary защищены агрегатом."""
        assignment = EnumAttributeAssignmentVO(self.attribute, self.options, False, 0)
        self.item.update(
            fields=frozenset({"attributes"}),
            actor=self.actor,
            now=self.now,
            attributes=(assignment,),
            definitions=self.definitions,
        )
        self.assertEqual(self.item.attributes, (assignment,))
        with self.assertRaises(InvalidCatalogValueError):
            self.item.update(
                fields=frozenset({"attributes"}),
                actor=self.actor,
                now=self.now,
                attributes=(assignment,),
                definitions=(),
            )
        with self.assertRaises(InvalidCatalogValueError):
            EnumAttributeAssignmentVO(self.attribute, (), True, 0)
        category = EntityIdVO(uuid4())
        self.item.update(
            fields=frozenset({"category_ids", "primary_category_id"}),
            actor=self.actor,
            now=self.now,
            category_ids=(category,),
            primary_category_id=category,
            existing_categories=frozenset({category}),
        )
        with self.assertRaises(InvalidCatalogValueError):
            self.item.update(
                fields=frozenset({"category_ids", "primary_category_id"}),
                actor=self.actor,
                now=self.now,
                category_ids=(category,),
                primary_category_id=None,
                existing_categories=frozenset({category}),
            )
        self.item.update(
            fields=frozenset({"category_ids", "primary_category_id"}),
            actor=self.actor,
            now=self.now,
            category_ids=(),
            primary_category_id=None,
            existing_categories=frozenset(),
        )
        self.item.update(
            fields=frozenset({"attributes"}),
            actor=self.actor,
            now=self.now,
            attributes=(),
            definitions=(),
        )
        self.item.update(
            fields=frozenset({"tag_ids"}),
            actor=self.actor,
            now=self.now,
            tag_ids=(category,),
            existing_tags=frozenset({category}),
        )
        with self.assertRaises(InvalidCatalogValueError):
            self.item.update(
                fields=frozenset({"tag_ids"}),
                actor=self.actor,
                now=self.now,
                tag_ids=(category, category),
                existing_tags=frozenset({category}),
            )

    def test_metadata_full_replacement_preserves_false_zero_and_order(self) -> None:
        """Metadata сохраняет тип, порядок и значения false/0, удаляется исключением из набора."""
        entries = (
            CatalogMetadataEntry.create("enabled", "boolean", False, 2),
            CatalogMetadataEntry.create("amount", "decimal", Decimal("0"), 1),
        )
        self.item.update(
            fields=frozenset({"metadata"}),
            actor=self.actor,
            now=self.now,
            metadata=entries,
        )
        self.assertEqual(
            [entry.key for entry in self.item.metadata], ["amount", "enabled"]
        )
        self.assertEqual(self.item.metadata[0].value, Decimal("0"))
        self.assertIs(self.item.metadata[1].value, False)
        for entry in (
            CatalogMetadataEntry.create("sku", "text", "x", 0),
            CatalogMetadataEntry.create("flag", "boolean", "false", 0),
            CatalogMetadataEntry.create("value", "decimal", Decimal("NaN"), 0),
        ):
            with self.assertRaises(InvalidCatalogValueError):
                self.item.update(
                    fields=frozenset({"metadata"}),
                    actor=self.actor,
                    now=self.now,
                    metadata=(entry,),
                )
        self.item.update(
            fields=frozenset({"metadata"}), actor=self.actor, now=self.now, metadata=()
        )
        self.assertEqual(self.item.metadata, ())

    def test_gallery_primary_order_unique_ids_and_preflight(self) -> None:
        """Главное принадлежит набору, preflight не меняет товар, locale независимы."""
        image = CatalogItemImage.create(
            EntityIdVO(uuid4()), EntityIdVO(uuid4()), 0, "alt", "caption"
        )
        before = self.item.snapshot()
        self.item.ensure_can_add_image(
            LocaleVO("en"), image, False, self.actor, self.now
        )
        self.assertEqual(self.item.snapshot(), before)
        self.item.add_image(LocaleVO("en"), image, False, self.actor, self.now)
        self.assertEqual(self.item.galleries["en"].primary_image_id, image.id)
        with self.assertRaises(InvalidCatalogValueError):
            self.item.update(
                fields=frozenset({"gallery"}),
                actor=self.actor,
                now=self.now,
                gallery=CatalogItemGallery.create((image,), image.id),
                locale=LocaleVO("ru"),
            )
        with self.assertRaises(InvalidCatalogValueError):
            self.item.update(
                fields=frozenset({"gallery"}),
                actor=self.actor,
                now=self.now,
                gallery=CatalogItemGallery.create(
                    self.item.galleries["en"].images, EntityIdVO(uuid4())
                ),
                locale=LocaleVO("en"),
            )
        self.item.update(
            fields=frozenset({"gallery"}),
            actor=self.actor,
            now=self.now,
            gallery=CatalogItemGallery.create((), None),
            locale=LocaleVO("en"),
        )
        self.assertEqual(self.item.galleries["en"].images, ())
        self.item.update(
            fields=frozenset({"gallery"}),
            actor=self.actor,
            now=self.now,
            gallery=None,
            locale=LocaleVO("en"),
        )
        self.assertNotIn("en", self.item.galleries)

    def test_persistence_round_trip_and_clear_storage(self) -> None:
        """SQL хранит simple/set, старые clear читаются как отсутствие без миграции."""
        self.item.update(
            fields=frozenset({"content"}),
            actor=self.actor,
            now=self.now,
            content={"name": "Name", "desc": ""},
            locale=LocaleVO("en"),
            schema=self.schema,
            expected_schema_version=1,
        )
        self.item.update(
            fields=frozenset({"sku"}),
            actor=self.actor,
            now=self.now,
            sku=SkuCodeVO(" SKU "),
        )
        self.item.update(
            fields=frozenset({"attributes"}),
            actor=self.actor,
            now=self.now,
            attributes=(
                EnumAttributeAssignmentVO(self.attribute, self.options, True, 0),
            ),
            definitions=self.definitions,
        )
        self.item.update(
            fields=frozenset({"metadata"}),
            actor=self.actor,
            now=self.now,
            metadata=(CatalogMetadataEntry.create("flag", "boolean", False, 0),),
        )
        row = CatalogItemMapper.to_insert_values(self.item)
        parts = CatalogItemMapper.to_parts(self.item)
        self.assertEqual(row["kind"], "simple")
        self.assertIsNone(row["parent_id"])
        self.assertNotIn("catalog_item_variant_selections", parts)
        self.assertNotIn("catalog_item_default_selections", parts)
        self.assertFalse(parts["catalog_item_attributes"][0]["is_variation"])
        values = CatalogItemMapper.to_values(row, parts)
        self.assertEqual(
            CatalogItemMapper.to_domain(values).snapshot(), self.item.snapshot()
        )
        for name in (
            "catalog_item_content_values",
            "catalog_item_attributes",
            "catalog_item_metadata",
        ):
            records = parts[name]
            for record in records:
                if name != "catalog_item_content_values" or record["value"] == "":
                    record["mode"] = "clear"
        values = CatalogItemMapper.to_values(row, parts)
        self.assertEqual(values.translations["en"], {"name": "Name"})
        self.assertEqual(values.attributes, ())
        self.assertEqual(values.metadata, ())
        details = CatalogItemQueryMapper.details(values, "en", self.now)
        publication = CatalogItemQueryMapper.publication(values, "en", self.now)
        self.assertNotEqual(type(details), type(publication))
        self.assertEqual(details.id, publication.id)
        self.assertEqual(details.content, {"name": "Name"})

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

    def test_atomic_multi_field_update_and_noop_audit(self) -> None:
        """Полный кандидат принимается один раз; повтор и ошибка не меняют audit."""
        before = self.item.snapshot()
        with self.assertRaises(InvalidCatalogValueError):
            self.item.update(
                fields=frozenset({"sku", "content"}),
                actor=self.actor,
                now=self.now + timedelta(seconds=1),
                sku=SkuCodeVO("candidate"),
                locale=LocaleVO("en"),
                content={"name": ""},
                schema=self.schema,
                expected_schema_version=1,
            )
        self.assertEqual(before, self.item.snapshot())
        self.item.update(
            fields=frozenset({"sku", "status", "virtual"}),
            actor=self.actor,
            now=self.now + timedelta(seconds=2),
            sku=SkuCodeVO("atomic"),
            status=CatalogItemStatus.ACTIVE,
            virtual=True,
        )
        accepted = self.item.snapshot()
        self.item.update(
            fields=frozenset({"sku", "status", "virtual"}),
            actor=EntityIdVO(uuid4()),
            now=self.now + timedelta(seconds=3),
            sku=SkuCodeVO("atomic"),
            status=CatalogItemStatus.ACTIVE,
            virtual=True,
        )
        self.assertEqual(accepted, self.item.snapshot())

    def test_equivalent_empty_dimensions_and_classification_sets_are_noops(
        self,
    ) -> None:
        """Канонические пустые размеры и неупорядоченные наборы не меняют audit."""
        self.item.update(
            fields=frozenset({"dimensions"}),
            dimensions=DimensionsVO(),
            actor=self.actor,
            now=self.now + timedelta(seconds=1),
        )
        self.assertEqual(self.item.updated_at, self.now)
        a, b = EntityIdVO(uuid4()), EntityIdVO(uuid4())
        self.item.update(
            fields=frozenset({"tag_ids"}),
            tag_ids=(a, b),
            existing_tags=frozenset({a, b}),
            actor=self.actor,
            now=self.now + timedelta(seconds=2),
        )
        before = self.item.snapshot()
        self.item.update(
            fields=frozenset({"tag_ids"}),
            tag_ids=(b, a),
            existing_tags=frozenset({a, b}),
            actor=self.actor,
            now=self.now + timedelta(seconds=3),
        )
        self.assertEqual(before, self.item.snapshot())
