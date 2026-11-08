"""Предложение поставщика, проверка источника и коммерческие условия заказа."""

import unittest
from dataclasses import FrozenInstanceError, fields, replace
from datetime import timedelta
from decimal import MAX_EMAX, Decimal, Inexact, Rounded, localcontext
from uuid import uuid4

from src.modules.shared.domain.value_object.currency import CurrencyVO
from src.modules.shared.domain.value_object.money import MoneyVO
from src.modules.supplier_sourcing.domain.supplier_offer.aggregate import SupplierOffer
from src.modules.supplier_sourcing.domain.supplier_offer.error import (
    InvalidSupplierOfferValueError,
    SupplierOfferInactiveError,
    SupplierOfferSourceMismatchError,
    SupplierOrderQuantityError,
)
from src.modules.supplier_sourcing.domain.supplier_offer.item_snapshot import (
    SupplierOfferItemSnapshot,
)
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.identifier import (
    SupplierOfferIdVO,
)
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.order_quantity import (
    SupplierOrderQuantityVO,
)
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.price_list_id import (
    SupplierPriceListIdVO,
)
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.supplier_sku import (
    SupplierSkuVO,
)
from src.modules.supplier_sourcing.domain.supplier_offer.value_object.uom_code import (
    SupplierOfferUomCodeVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.aggregate import (
    SupplierSource,
)
from src.modules.supplier_sourcing.domain.supplier_source.error import (
    InvalidSupplierSourceValueError,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.fulfillment_mode import (
    SupplierFulfillmentMode,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.name import (
    SupplierSourceNameVO,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.stock_update_policy import (
    MissingSkuBehavior,
    StaleStockBehavior,
    SupplierStockUpdatePolicyVO,
)
from src.modules.supplier_sourcing.domain.value_object.inventory_item_id import (
    SupplierInventoryItemIdVO,
)
from src.modules.supplier_sourcing.domain.value_object.lead_time import (
    SupplierLeadTimeVO,
)
from src.modules.supplier_sourcing.domain.value_object.supplier_id import SupplierIdVO


class SupplierOfferDomainTests(unittest.TestCase):
    """Проверяет условия закупки, жизненный цикл и связь с товаром и источником."""

    def setUp(self) -> None:
        """Готовит предложение с минимумом 10 PCS и кратностью 6 PCS."""
        self.supplier_id = SupplierIdVO(uuid4())
        self.item = SupplierOfferItemSnapshot(
            SupplierInventoryItemIdVO(uuid4()), SupplierOfferUomCodeVO("PCS")
        )
        self.offer = self.create()

    def create(self, **changes: object) -> SupplierOffer:
        """Создаёт предложение через публичную фабрику с явными коммерческими полями."""
        return SupplierOffer.create(
            **(
                dict(
                    identifier=SupplierOfferIdVO(uuid4()),
                    supplier_id=self.supplier_id,
                    item=self.item,
                    supplier_sku=SupplierSkuVO(" 001-AbC "),
                    purchase_price=MoneyVO(Decimal("120.05"), CurrencyVO("UAH")),
                    min_order_qty=SupplierOrderQuantityVO(Decimal(10)),
                    order_multiple=SupplierOrderQuantityVO(Decimal(6)),
                    lead_time=SupplierLeadTimeVO(timedelta(days=1)),
                    priority=0,
                )
                | changes
            )
        )

    def source(self, supplier_id: SupplierIdVO) -> SupplierSource:
        """Создаёт действительный источник, из которого предложение получит снимок."""
        return SupplierSource.create(
            identifier=SupplierSourceIdVO(uuid4()),
            supplier_id=supplier_id,
            name=SupplierSourceNameVO("Киев"),
            fulfillment_modes=frozenset({SupplierFulfillmentMode.DROPSHIP}),
            stock_update_policy=SupplierStockUpdatePolicyVO(
                timedelta(hours=2),
                StaleStockBehavior.MARK_UNKNOWN,
                MissingSkuBehavior.KEEP_LAST,
            ),
            default_lead_time=SupplierLeadTimeVO(timedelta(days=2)),
        )

    def restore(self, offer: SupplierOffer, **changes: object) -> SupplierOffer:
        """Восстанавливает весь сохранённый состав без загрузки товара и источника."""
        values = {field.name: getattr(offer, field.name) for field in fields(offer)}
        values["identifier"] = values.pop("id")
        return SupplierOffer.restore(**(values | changes))

    def test_two_suppliers_can_offer_same_item_with_separate_terms(self) -> None:
        """Цена, валюта, условия и исходный SKU принадлежат конкретному предложению."""
        second = self.create(
            supplier_id=SupplierIdVO(uuid4()),
            supplier_sku=SupplierSkuVO("001-abc"),
            purchase_price=MoneyVO(Decimal("3.25"), CurrencyVO("USD")),
            min_order_qty=SupplierOrderQuantityVO(Decimal(4)),
            order_multiple=SupplierOrderQuantityVO(Decimal(2)),
        )
        self.assertEqual(self.offer.inventory_item_id, second.inventory_item_id)
        self.assertEqual(self.offer.base_uom, self.item.base_uom)
        self.assertEqual(second.base_uom, self.item.base_uom)
        self.assertNotEqual(self.offer.supplier_id, second.supplier_id)
        self.assertNotEqual(
            self.offer.purchase_price.currency, second.purchase_price.currency
        )
        self.assertNotEqual(self.offer.min_order_qty, second.min_order_qty)
        self.assertEqual(self.offer.supplier_sku.value, "001-AbC")
        self.assertNotEqual(self.offer.supplier_sku, second.supplier_sku)
        self.assertTrue(self.offer.is_active and second.is_active)

    def test_optional_source_must_belong_to_supplier(self) -> None:
        """При наличии источника фабрика проверяет его принадлежность по снимку."""
        source = self.source(self.supplier_id)
        price_list_id = SupplierPriceListIdVO(uuid4())
        offer = self.create(
            source=source.identity_snapshot(), price_list_id=price_list_id
        )
        self.assertEqual(offer.source_id, source.id)
        self.assertEqual(offer.price_list_id, price_list_id)
        self.assertIsNone(self.offer.source_id)
        self.assertIsNone(self.offer.price_list_id)
        foreign = self.source(SupplierIdVO(uuid4()))
        with self.assertRaises(SupplierOfferSourceMismatchError):
            self.create(source=foreign.identity_snapshot())
        with self.assertRaises(InvalidSupplierOfferValueError):
            self.create(source=source)
        with self.assertRaises(InvalidSupplierSourceValueError):
            self.create(source=replace(source.identity_snapshot(), id=source.id.uuid))

    def test_minimum_is_independent_of_multiples_from_zero(self) -> None:
        """Шесть кратно, но мало, десять достигает минимума, но первый заказ равен двенадцати."""
        for value in ("6", "10", "11", "17"):
            with (
                self.subTest(value=value),
                self.assertRaises(SupplierOrderQuantityError),
            ):
                self.offer.ensure_order_quantity(
                    SupplierOrderQuantityVO(Decimal(value)), uom=self.item.base_uom
                )
        for value in ("12", "18.00", "24"):
            with self.subTest(value=value):
                self.offer.ensure_order_quantity(
                    SupplierOrderQuantityVO(Decimal(value)), uom=self.item.base_uom
                )

    def test_rejects_quantities_in_wrong_or_untyped_units(self) -> None:
        """Сравнение чисел допустимо только в базовой единице предложения."""
        quantity = SupplierOrderQuantityVO(Decimal(12))
        for value, uom in (
            (quantity, SupplierOfferUomCodeVO("BOX")),
            (quantity, "PCS"),
            (Decimal(12), self.item.base_uom),
        ):
            with (
                self.subTest(value=value, uom=uom),
                self.assertRaises(SupplierOrderQuantityError),
            ):
                self.offer.ensure_order_quantity(value, uom=uom)

    def test_fractional_multiples_are_exact_under_small_decimal_context(self) -> None:
        """Коммерческий шаг работает с дробями и не зависит от округления Decimal."""
        item = replace(self.item, base_uom=SupplierOfferUomCodeVO("KG"))
        offer = self.create(
            item=item,
            min_order_qty=SupplierOrderQuantityVO(Decimal("0.10")),
            order_multiple=SupplierOrderQuantityVO(Decimal("0.03")),
        )
        with localcontext() as context:
            context.prec = 1
            context.traps[Inexact] = True
            context.traps[Rounded] = True
            offer.ensure_order_quantity(
                SupplierOrderQuantityVO(Decimal("0.120")), uom=item.base_uom
            )
            huge_multiple = Decimal((0, (3,), MAX_EMAX))
            offer.ensure_order_quantity(
                SupplierOrderQuantityVO(huge_multiple), uom=item.base_uom
            )
            with self.assertRaises(SupplierOrderQuantityError):
                offer.ensure_order_quantity(
                    SupplierOrderQuantityVO(Decimal("0.1200001")), uom=item.base_uom
                )

    def test_price_and_terms_change_without_altering_previous_conditions(self) -> None:
        """Новая цена и условия сохраняют идентичность и исходное сопоставление."""
        source = self.source(self.supplier_id)
        original = self.create(source=source.identity_snapshot())
        free_price = MoneyVO(Decimal(0), CurrencyVO("UAH"))
        updated = original.change_purchase_price(free_price).configure_order_terms(
            min_order_qty=SupplierOrderQuantityVO(Decimal(4)),
            order_multiple=SupplierOrderQuantityVO(Decimal(2)),
            lead_time=SupplierLeadTimeVO(timedelta(days=3)),
            priority=5,
        )
        self.assertEqual(updated.purchase_price, free_price)
        self.assertEqual(updated.priority, 5)
        self.assertEqual(updated.lead_time.value, timedelta(days=3))
        updated.ensure_order_quantity(
            SupplierOrderQuantityVO(Decimal(4)), uom=updated.base_uom
        )
        self.assertEqual(
            (
                updated.id,
                updated.inventory_item_id,
                updated.source_id,
                updated.supplier_sku,
            ),
            (
                original.id,
                original.inventory_item_id,
                original.source_id,
                original.supplier_sku,
            ),
        )
        self.assertEqual(original.purchase_price.amount, Decimal("120.05"))
        with self.assertRaises(InvalidSupplierOfferValueError):
            updated.change_purchase_price(MoneyVO(Decimal(-1), CurrencyVO("UAH")))
        self.assertEqual(updated.purchase_price, free_price)

    def test_restores_inactive_offer_and_allows_reactivation(self) -> None:
        """Восстановление сохраняет блокировку, цену и все ссылки предложения."""
        source = self.source(self.supplier_id)
        original = self.create(
            source=source.identity_snapshot(),
            price_list_id=SupplierPriceListIdVO(uuid4()),
        )
        inactive = original.deactivate()
        restored = self.restore(inactive)
        self.assertEqual(restored, inactive)
        self.assertEqual(restored.deactivate(), inactive)
        with self.assertRaises(SupplierOfferInactiveError):
            restored.ensure_order_quantity(
                SupplierOrderQuantityVO(Decimal(12)), uom=self.item.base_uom
            )
        self.assertEqual(restored.activate(), original)
        with self.assertRaises(FrozenInstanceError):
            restored.source_id = None

    def test_rejects_incorrect_snapshot_price_priority_and_links(self) -> None:
        """Идентификаторы, снимки, деньги и приоритет проверяются на границах фабрик."""
        for changes in (
            dict(item=self.item.inventory_item_id),
            dict(item=replace(self.item, inventory_item_id=self.supplier_id)),
            dict(item=replace(self.item, base_uom="PCS")),
            dict(supplier_sku="001-AbC"),
            dict(price_list_id=self.offer.id),
            dict(purchase_price=MoneyVO(Decimal(-1), CurrencyVO("UAH"))),
            dict(purchase_price=Decimal(1)),
            dict(min_order_qty=Decimal(10)),
            dict(order_multiple=None),
            dict(priority=-1),
            dict(priority=False),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidSupplierOfferValueError),
            ):
                self.create(**changes)
        for changes in (
            dict(is_active=1),
            dict(source_id=self.offer.id),
            dict(base_uom="PCS"),
        ):
            with (
                self.subTest(changes=changes),
                self.assertRaises(InvalidSupplierOfferValueError),
            ):
                self.restore(self.offer, **changes)

    def test_quantity_sku_and_unit_value_objects_reject_bad_input(self) -> None:
        """Значения отклоняют неявные преобразования, пустоту и нечисловые количества."""
        for value in (
            True,
            1,
            None,
            Decimal(0),
            Decimal(-1),
            Decimal("sNaN"),
            Decimal("Infinity"),
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(SupplierOrderQuantityError),
            ):
                SupplierOrderQuantityVO(value)
        for factory in (SupplierSkuVO, SupplierOfferUomCodeVO):
            for value in ("  ", "A\x7f", 123, None):
                with (
                    self.subTest(factory=factory, value=value),
                    self.assertRaises(InvalidSupplierOfferValueError),
                ):
                    factory(value)
