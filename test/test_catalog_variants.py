"""Инварианты семьи и источники наследования без SQL и HTTP."""

from dataclasses import replace
from datetime import datetime, UTC, timedelta
from decimal import Decimal
import unittest
from uuid import uuid4
from test.catalog_support import default_schema
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.entity.variant import CatalogVariant
from src.modules.catalog.domain.catalog_item.entity.gallery import CatalogItemGallery
from src.modules.catalog.domain.catalog_item.entity.image import CatalogItemImage
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.catalog_item.value_object.kind import (
    CatalogItemKind,
)
from src.modules.catalog.domain.catalog_item.value_object.status import (
    CatalogItemStatus,
)
from src.modules.catalog.domain.catalog_item.value_object.sku import SkuCodeVO
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockSpecificationVO,
    StockStatus,
    BackorderPolicy,
)
from src.modules.catalog.domain.catalog_item.value_object.measurements import (
    WeightVO,
    WeightUnit,
    DimensionsVO,
    LengthVO,
    LengthUnit,
)
from src.modules.catalog.domain.catalog_item.policy.variant_values import (
    effective_variant,
)
from src.modules.catalog.domain.catalog_item.policy.values import (
    CatalogItemValuesPolicy,
)
from src.modules.catalog.domain.value_object.locale import LocaleVO
from src.modules.catalog.domain.error import (
    InvalidCatalogValueError,
    CatalogConflictError,
    CatalogNotFoundError,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.mapper import (
    CatalogItemMapper,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.query_mapper import (
    CatalogItemQueryMapper,
)


class CatalogVariantDomainTests(unittest.TestCase):
    """Проверяет атомарность и отсутствие материализации родительских значений."""

    def setUp(self) -> None:
        """Создаёт контейнер с одним полностью наследующим Draft-вариантом."""
        self.actor = EntityIdVO(uuid4())
        self.now = datetime(2026, 10, 28, tzinfo=UTC)
        self.schema = default_schema()
        self.root = CatalogItem.create_variable(
            identifier=CatalogItemIdVO(uuid4()),
            actor=self.actor,
            now=self.now,
            product_type_id=self.schema.id,
        )
        self.root.update(
            fields=frozenset({"content", "stock", "weight"}),
            actor=self.actor,
            now=self.now,
            locale=LocaleVO("en"),
            content={"title": "Active shirt", "body": "Common body"},
            schema=self.schema,
            expected_schema_version=1,
            stock=StockSpecificationVO(True, 7, None, BackorderPolicy.NO),
            weight=WeightVO(Decimal("1"), WeightUnit.KG),
        )
        self.variant = CatalogVariant.create(
            identifier=CatalogItemIdVO(uuid4()),
            parent_id=self.root.id,
            actor=self.actor,
            now=self.now,
        )
        self.root.add_variant(
            variant=self.variant, actor=self.actor, now=self.now, schema=self.schema
        )

    def effective(self, variant: CatalogVariant | None = None, locale: str = "en"):
        """Возвращает чистое вычисление на актуальном родителе."""
        return effective_variant(
            self.root.snapshot(),
            (variant or self.variant).snapshot(self.schema.id),
            locale,
        )

    def test_default_inheritance_and_parent_changes(self) -> None:
        """Все локализованные разделы наследуются без изменения собственных данных."""
        image = CatalogItemImage.create(EntityIdVO(uuid4()), EntityIdVO(uuid4()), 0)
        gallery = CatalogItemGallery.create((image,), image.id)
        self.root.update(
            fields=frozenset({"gallery"}),
            actor=self.actor,
            now=self.now,
            locale=LocaleVO("en"),
            gallery=gallery,
        )
        effective = self.effective()
        self.assertEqual(effective.values.translations["en"]["title"], "Active shirt")
        self.assertEqual(effective.gallery_source_id, self.root.id)
        self.assertEqual(effective.stock_source_id, self.root.id)
        self.assertEqual(effective.values.stock.stock_quantity, 7)
        self.assertEqual(self.variant.translations, {})
        self.assertEqual(self.variant.galleries, {})
        self.assertEqual(self.variant.stock, StockSpecificationVO())
        self.assertEqual(self.effective(locale="ru").values.translations, {})
        before = self.variant
        self.root.update(
            fields=frozenset({"content"}),
            actor=self.actor,
            now=self.now + timedelta(seconds=1),
            locale=LocaleVO("en"),
            content={"title": "Updated", "body": "Changed"},
            schema=self.schema,
            expected_schema_version=1,
        )
        self.assertEqual(self.effective().values.translations["en"]["title"], "Updated")
        self.assertEqual(self.root.variant(self.variant.id), before)

    def test_independent_overrides_clear_and_reset(self) -> None:
        """Своё название не блокирует родительское описание; пустые разделы явные."""
        own = self.variant.changed(
            fields=frozenset({"content", "gallery"}),
            actor=self.actor,
            now=self.now,
            locale=LocaleVO("en"),
            content={"title": "Red L"},
            gallery=CatalogItemGallery.create((), None),
        )
        self.root.change_variant(
            variant=own, actor=self.actor, now=self.now, schema=self.schema
        )
        result = self.effective(own)
        self.assertEqual(
            result.values.translations["en"], {"title": "Red L", "body": "Common body"}
        )
        self.assertEqual(result.title_source_id, own.id)
        self.assertEqual(result.body_source_id, self.root.id)
        self.assertEqual(result.values.galleries["en"].images, ())
        clear = own.changed(
            fields=frozenset({"content"}),
            actor=self.actor,
            now=self.now,
            locale=LocaleVO("en"),
            content={"body": ""},
        )
        self.root.change_variant(
            variant=clear, actor=self.actor, now=self.now, schema=self.schema
        )
        self.assertEqual(
            self.effective(clear).values.translations["en"],
            {"title": "Active shirt", "body": ""},
        )
        reset = clear.changed(
            fields=frozenset({"content", "gallery"}),
            actor=self.actor,
            now=self.now,
            locale=LocaleVO("en"),
            content=None,
            gallery=None,
        )
        self.assertEqual(self.effective(reset).title_source_id, self.root.id)
        self.assertEqual(self.effective(reset).body_source_id, self.root.id)
        with self.assertRaises(InvalidCatalogValueError):
            self.variant.changed(
                fields=frozenset({"content"}),
                actor=self.actor,
                now=self.now,
                locale=LocaleVO("en"),
                content={"title": ""},
            )

    def test_stock_and_measurement_sources(self) -> None:
        """Переключение требует stock и не копирует отдельные размеры родителя."""
        with self.assertRaises(InvalidCatalogValueError):
            self.variant.changed(
                fields=frozenset({"stock"}), actor=self.actor, now=self.now, stock=None
            )
        own = self.variant.changed(
            fields=frozenset({"stock", "weight"}),
            actor=self.actor,
            now=self.now,
            stock=StockSpecificationVO(True, 2, None, BackorderPolicy.NO),
            weight=WeightVO(Decimal("100"), WeightUnit.G),
        )
        cleared = own.changed(
            fields=frozenset({"dimensions"}),
            actor=self.actor,
            now=self.now,
            dimensions=DimensionsVO(None, None, None),
        )
        self.assertIsNone(cleared.dimensions)
        self.assertEqual(self.effective(own).stock_source_id, own.id)
        inherited = own.changed(
            fields=frozenset({"stock", "weight"}),
            actor=self.actor,
            now=self.now,
            stock=StockSpecificationVO(False, None, StockStatus.OUT_OF_STOCK),
            weight=None,
        )
        self.assertEqual(inherited.stock.stock_status, StockStatus.OUT_OF_STOCK)
        self.assertEqual(self.effective(inherited).stock_source_id, self.root.id)
        self.assertEqual(self.effective(inherited).values.weight, self.root.weight)
        self.root.update(
            fields=frozenset({"stock"}),
            actor=self.actor,
            now=self.now,
            stock=StockSpecificationVO(),
        )
        self.assertEqual(self.effective(inherited).stock_source_id, inherited.id)
        self.assertEqual(
            self.effective(inherited).values.stock.stock_status,
            StockStatus.OUT_OF_STOCK,
        )

    def test_stock_priority_matrix_and_backorders(self) -> None:
        """Собственный учёт побеждает родительский, ручной статус сохраняется."""
        manual = StockSpecificationVO(False, None, StockStatus.ON_BACKORDER)
        for parent_manage in (False, True):
            for own_manage in (False, True):
                for quantity, backorders in (
                    (5, BackorderPolicy.NO),
                    (0, BackorderPolicy.NO),
                    (-2, BackorderPolicy.YES),
                    (0, BackorderPolicy.NOTIFY),
                ):
                    parent = replace(
                        self.root.snapshot(),
                        stock=(
                            StockSpecificationVO(True, quantity, None, backorders)
                            if parent_manage
                            else StockSpecificationVO(
                                False, None, StockStatus.OUT_OF_STOCK
                            )
                        ),
                    )
                    own_stock = (
                        StockSpecificationVO(True, quantity, None, backorders)
                        if own_manage
                        else manual
                    )
                    own = replace(
                        self.variant.snapshot(self.schema.id), stock=own_stock
                    )
                    effective = effective_variant(parent, own, "en")
                    inherited = parent_manage and not own_manage
                    self.assertEqual(
                        effective.stock_source_id, parent.id if inherited else own.id
                    )
                    self.assertEqual(
                        effective.values.stock, parent.stock if inherited else own_stock
                    )
                    self.assertEqual(own.stock, own_stock)
                    dto = CatalogItemQueryMapper.variant(parent, own, "en", self.now)
                    self.assertEqual(dto.stock, own_stock)
                    self.assertEqual(dto.effective_stock, effective.values.stock)
                    self.assertEqual(dto.stock_source, "parent" if inherited else "own")
                    self.assertEqual(
                        dto.stock_status,
                        effective.values.stock.effective_status().value,
                    )

    def test_last_variant_status_and_atomic_errors(self) -> None:
        """Последняя неархивная позиция защищена, статусы детей не переписываются."""
        self.root.update(
            fields=frozenset({"status"}),
            actor=self.actor,
            now=self.now,
            status=CatalogItemStatus.ACTIVE,
        )
        before = self.root.variants
        with self.assertRaises(InvalidCatalogValueError):
            self.root.remove_variant(
                identifier=self.variant.id, actor=self.actor, now=self.now
            )
        archived = replace(self.variant, status=CatalogItemStatus.ARCHIVED)
        with self.assertRaises(InvalidCatalogValueError):
            self.root.change_variant(variant=archived, actor=self.actor, now=self.now)
        self.assertEqual(self.root.variants, before)
        self.root.update(
            fields=frozenset({"status"}),
            actor=self.actor,
            now=self.now,
            status=CatalogItemStatus.ARCHIVED,
        )
        self.assertEqual(
            self.root.variant(self.variant.id).status, CatalogItemStatus.DRAFT
        )
        self.root.remove_variant(
            identifier=self.variant.id, actor=self.actor, now=self.now
        )
        self.assertEqual(self.root.variants, ())
        with self.assertRaises(InvalidCatalogValueError):
            self.root.update(
                fields=frozenset({"status"}),
                actor=self.actor,
                now=self.now,
                status=CatalogItemStatus.ACTIVE,
            )

    def test_family_membership_sku_and_price(self) -> None:
        """Чужая entity, дубли SKU и цена контейнера отклоняются без изменений."""
        with self.assertRaises(InvalidCatalogValueError):
            self.root.add_variant(
                variant=replace(
                    self.variant,
                    id=CatalogItemIdVO(uuid4()),
                    parent_id=CatalogItemIdVO(uuid4()),
                ),
                actor=self.actor,
                now=self.now,
                schema=self.schema,
            )
        with self.assertRaises(CatalogNotFoundError):
            self.root.variant(CatalogItemIdVO(uuid4()))
        self.root.update(
            fields=frozenset({"sku"}),
            actor=self.actor,
            now=self.now,
            sku=SkuCodeVO("PARENT"),
        )
        with self.assertRaises(CatalogConflictError):
            self.root.change_variant(
                variant=replace(self.variant, sku=SkuCodeVO("PARENT")),
                actor=self.actor,
                now=self.now,
            )
        with self.assertRaises(InvalidCatalogValueError):
            self.root.update(
                fields=frozenset({"price_specification"}),
                actor=self.actor,
                now=self.now,
                price_specification=PriceSpecificationVO(Decimal("1"), "UAH"),
            )
        self.assertIsNone(self.root.price)

    def test_effective_availability_and_exact_price(self) -> None:
        """Собственная цена точна, а родительский статус ограничивает продажу."""
        variant = replace(
            self.variant,
            status=CatalogItemStatus.ACTIVE,
            price=PriceSpecificationVO(Decimal("99999.123456"), "UAH"),
        )
        self.assertFalse(
            CatalogItemValuesPolicy.calculate(
                self.effective(variant).values, self.now
            ).available_for_sale
        )
        self.root.update(
            fields=frozenset({"status"}),
            actor=self.actor,
            now=self.now,
            status=CatalogItemStatus.ACTIVE,
        )
        self.assertTrue(
            CatalogItemValuesPolicy.calculate(
                self.effective(variant).values, self.now
            ).available_for_sale
        )
        dto = CatalogItemQueryMapper.variant(
            self.root.snapshot(), variant.snapshot(self.schema.id), "en", self.now
        )
        self.assertEqual(dto.stock, StockSpecificationVO())
        self.assertEqual(dto.effective_stock.stock_quantity, 7)
        self.assertEqual(dto.sources.title, self.root.id.uuid)
        self.assertEqual(dto.price, Decimal("99999.123456"))
        self.assertEqual(dto.status, CatalogItemStatus.ACTIVE)

    def test_persistence_keeps_only_own_values(self) -> None:
        """Mapper сохраняет роль, parent и пустые собственные остатки варианта."""
        row = CatalogItemMapper.to_insert_values(self.variant)
        self.assertEqual(
            (row["kind"], row["parent_id"]),
            ("variant", self.root.id.uuid),
        )
        self.assertFalse(row["manage_stock"])
        self.assertNotIn("stock_source", row)
        self.assertIsNone(row["product_type_id"])
        own = CatalogItemMapper.to_values(
            row,
            {
                name: []
                for name in (
                    "catalog_item_translations",
                    "catalog_item_content_values",
                    "catalog_item_galleries",
                    "catalog_item_images",
                )
            },
            self.schema.id,
        )
        restored = CatalogItemMapper.to_variant(own)
        self.assertEqual(restored, self.variant)
        self.assertEqual(
            CatalogItemMapper.to_parts(restored, {}).get("catalog_item_content_values"),
            [],
        )
