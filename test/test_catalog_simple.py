from test.catalog_support import default_schema

"""Регрессия самостоятельных товаров без наследования и вариативных сценариев."""

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from decimal import Decimal, localcontext
import unittest
from uuid import uuid4
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.catalog.domain.catalog_item.entity.image import CatalogItemImage
from src.modules.catalog.domain.catalog_item.policy.values import (
    CatalogItemValuesPolicy,
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
from src.modules.catalog.domain.error import (
    CatalogConflictError,
    InvalidCatalogValueError,
)
from src.modules.catalog.domain.product_type.value_object.schema import (
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
        self.schema = default_schema()
        self.item = CatalogItem.create(
            CatalogItemIdVO(uuid4()), self.actor, self.now, self.schema.id
        )

    def test_creation_and_restore_validate_one_item(self) -> None:
        """Простой корень не содержит вариантов; восстановление проверяет инварианты."""
        self.assertFalse(hasattr(self.item, "revision"))
        self.assertEqual(self.item.product_type_id, self.schema.id)
        self.assertFalse(self.item.stock.manage_stock)
        self.assertEqual(self.item.stock.effective_status(), StockStatus.IN_STOCK)
        self.assertFalse(
            {"parent_id", "children", "axes", "selection"}
            & {f.name for f in fields(self.item) if f.init}
        )
        self.assertEqual(self.item.kind.value, "simple")
        self.assertEqual(self.item.variants, ())
        values = {
            f.name: getattr(self.item, f.name) for f in fields(self.item) if f.init
        }
        values["identifier"] = values.pop("id")
        restored = CatalogItem.restore(**values)
        self.assertEqual(restored.snapshot(), self.item.snapshot())
        for changes in (
            {"product_type_id": None},
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
                content={"body": "No name"},
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

    def test_content_full_replacement_locale_and_empty_text(self) -> None:
        """Переводы независимы, отсутствие удаляет optional блок, пустой текст сохраняется."""
        self.item.update(
            fields=frozenset({"content"}),
            actor=self.actor,
            now=self.now,
            content={"title": "Name", "body": ""},
            locale=LocaleVO("en"),
            schema=self.schema,
            expected_schema_version=1,
        )
        self.item.update(
            fields=frozenset({"content"}),
            actor=self.actor,
            now=self.now,
            content={"title": "Имя"},
            locale=LocaleVO("ru"),
            schema=self.schema,
            expected_schema_version=1,
        )
        self.item.update(
            fields=frozenset({"content"}),
            actor=self.actor,
            now=self.now,
            content={"title": "New", "body": ""},
            locale=LocaleVO("en"),
            schema=self.schema,
            expected_schema_version=1,
        )
        self.assertEqual(self.item.translations["en"], {"title": "New", "body": ""})
        self.assertEqual(self.item.translations["ru"]["title"], "Имя")
        with self.assertRaises(CatalogConflictError):
            self.item.update(
                fields=frozenset({"content"}),
                actor=self.actor,
                now=self.now,
                content={"title": "Name"},
                locale=LocaleVO("en"),
                schema=self.schema,
                expected_schema_version=2,
            )
        for content in (
            {"title": " "},
            {"title": "x" * 256},
            {"title": "Name", "extra": "x"},
            {"title": {"mode": "set", "value": "Name"}},
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
            content={"title": "Name", "body": ""},
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
        row = CatalogItemMapper.to_insert_values(self.item)
        parts = CatalogItemMapper.to_parts(
            self.item, {block.code: block.id.uuid for block in self.schema.blocks}
        )
        codes = {block.id.uuid: block.code for block in self.schema.blocks}
        for record in parts["catalog_item_content_values"]:
            record["block_code"] = codes[record["block_id"]]
        self.assertEqual(row["kind"], "simple")
        self.assertIsNone(row["parent_id"])
        self.assertNotIn("catalog_item_variant_selections", parts)
        self.assertNotIn("catalog_item_default_selections", parts)
        values = CatalogItemMapper.to_values(row, parts)
        self.assertEqual(
            CatalogItemMapper.to_domain(values, self.schema).snapshot(),
            self.item.snapshot(),
        )
        for name in ("catalog_item_content_values",):
            records = parts[name]
            for record in records:
                if name != "catalog_item_content_values" or record["value"] == "":
                    record["mode"] = "clear"
        values = CatalogItemMapper.to_values(row, parts)
        self.assertEqual(values.translations["en"], {"title": "Name"})
        details = CatalogItemQueryMapper.details(values, "en", self.now)
        self.assertEqual(details.content, {"title": "Name"})

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
                content={"title": ""},
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

    def test_equivalent_empty_dimensions_are_noops(
        self,
    ) -> None:
        """Канонические пустые размеры не меняют audit."""
        self.item.update(
            fields=frozenset({"dimensions"}),
            dimensions=DimensionsVO(),
            actor=self.actor,
            now=self.now + timedelta(seconds=1),
        )
        self.assertEqual(self.item.updated_at, self.now)
