from src.modules.supplier_sourcing.domain.value_object.supplier_reference import (
    SupplierReferenceVO,
)
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Self

from src.modules.shared.domain.decimal_arithmetic import is_decimal_multiple
from src.modules.shared.domain.value_object.money import MoneyVO
from src.modules.supplier_sourcing.domain.supplier_offer.availability_snapshot import (
    SupplierOfferAvailabilitySnapshot,
)
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
from src.modules.supplier_sourcing.domain.supplier_source.identity_snapshot import (
    SupplierSourceIdentitySnapshot,
)
from src.modules.supplier_sourcing.domain.supplier_source.value_object.identifier import (
    SupplierSourceIdVO,
)
from src.modules.supplier_sourcing.domain.value_object.inventory_item_id import (
    SupplierInventoryItemIdVO,
)
from src.modules.supplier_sourcing.domain.value_object.lead_time import (
    SupplierLeadTimeVO,
)


@dataclass(frozen=True, slots=True)
class SupplierOffer:
    """Связывает внешний SKU с товаром и фиксирует текущие условия закупки."""

    id: SupplierOfferIdVO
    supplier: SupplierReferenceVO
    inventory_item_id: SupplierInventoryItemIdVO
    supplier_sku: SupplierSkuVO
    base_uom: SupplierOfferUomCodeVO
    price_list_id: SupplierPriceListIdVO | None
    source_id: SupplierSourceIdVO | None
    purchase_price: MoneyVO
    min_order_qty: SupplierOrderQuantityVO
    order_multiple: SupplierOrderQuantityVO
    lead_time: SupplierLeadTimeVO
    priority: int
    is_active: bool

    @classmethod
    def create(
        cls,
        *,
        identifier: SupplierOfferIdVO,
        supplier: SupplierReferenceVO,
        item: SupplierOfferItemSnapshot,
        supplier_sku: SupplierSkuVO,
        purchase_price: MoneyVO,
        min_order_qty: SupplierOrderQuantityVO,
        order_multiple: SupplierOrderQuantityVO,
        lead_time: SupplierLeadTimeVO,
        priority: int,
        source: SupplierSourceIdentitySnapshot | None = None,
        price_list_id: SupplierPriceListIdVO | None = None,
    ) -> Self:
        """Создаёт активное предложение по снимку товара и проверяет принадлежность источника."""
        if not isinstance(item, SupplierOfferItemSnapshot):
            raise InvalidSupplierOfferValueError("Нужен снимок товара предложения.")
        item.ensure_valid()
        source_id = None
        if source is not None:
            if not isinstance(source, SupplierSourceIdentitySnapshot):
                raise InvalidSupplierOfferValueError(
                    "Нужен снимок идентичности источника."
                )
            source.ensure_valid()
            if source.supplier != supplier:
                raise SupplierOfferSourceMismatchError(
                    "Источник предложения должен принадлежать тому же поставщику."
                )
            source_id = source.id
        return cls.restore(
            identifier=identifier,
            supplier=supplier,
            inventory_item_id=item.inventory_item_id,
            supplier_sku=supplier_sku,
            base_uom=item.base_uom,
            price_list_id=price_list_id,
            source_id=source_id,
            purchase_price=purchase_price,
            min_order_qty=min_order_qty,
            order_multiple=order_multiple,
            lead_time=lead_time,
            priority=priority,
            is_active=True,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: SupplierOfferIdVO,
        supplier: SupplierReferenceVO,
        inventory_item_id: SupplierInventoryItemIdVO,
        supplier_sku: SupplierSkuVO,
        base_uom: SupplierOfferUomCodeVO,
        price_list_id: SupplierPriceListIdVO | None,
        source_id: SupplierSourceIdVO | None,
        purchase_price: MoneyVO,
        min_order_qty: SupplierOrderQuantityVO,
        order_multiple: SupplierOrderQuantityVO,
        lead_time: SupplierLeadTimeVO,
        priority: int,
        is_active: bool,
    ) -> Self:
        """Восстанавливает сохранённое предложение по его собственным полям."""
        offer = cls(
            id=identifier,
            supplier=supplier,
            inventory_item_id=inventory_item_id,
            supplier_sku=supplier_sku,
            base_uom=base_uom,
            price_list_id=price_list_id,
            source_id=source_id,
            purchase_price=purchase_price,
            min_order_qty=min_order_qty,
            order_multiple=order_multiple,
            lead_time=lead_time,
            priority=priority,
            is_active=is_active,
        )
        offer._validate()
        return offer

    def availability_snapshot(self) -> SupplierOfferAvailabilitySnapshot:
        """Возвращает контекст проверки наблюдений наличия предложения."""
        self._validate()
        return SupplierOfferAvailabilitySnapshot(
            self.id, self.supplier, self.source_id, self.base_uom
        )

    def change_purchase_price(self, purchase_price: MoneyVO) -> Self:
        """Возвращает предложение с текущей ценой за базовую единицу товара."""
        return self._with_changes(purchase_price=purchase_price)

    def configure_order_terms(
        self,
        *,
        min_order_qty: SupplierOrderQuantityVO,
        order_multiple: SupplierOrderQuantityVO,
        lead_time: SupplierLeadTimeVO,
        priority: int,
    ) -> Self:
        """Меняет минимум, кратность, срок и приоритет без изменения сопоставления товара."""
        return self._with_changes(
            min_order_qty=min_order_qty,
            order_multiple=order_multiple,
            lead_time=lead_time,
            priority=priority,
        )

    def activate(self) -> Self:
        """Разрешает использование предложения для заказа."""
        return self._with_changes(is_active=True)

    def deactivate(self) -> Self:
        """Блокирует использование предложения для заказа."""
        return self._with_changes(is_active=False)

    def ensure_order_quantity(
        self, quantity: SupplierOrderQuantityVO, *, uom: SupplierOfferUomCodeVO
    ) -> None:
        """Проверяет активность, базовую единицу, минимум и коммерческую кратность."""
        self._validate()
        if not self.is_active:
            raise SupplierOfferInactiveError("Предложение поставщика деактивировано.")
        if (
            not isinstance(quantity, SupplierOrderQuantityVO)
            or not isinstance(uom, SupplierOfferUomCodeVO)
            or uom != self.base_uom
        ):
            raise SupplierOrderQuantityError(
                "Нужно типизированное количество в базовой единице предложения."
            )
        if quantity.value < self.min_order_qty.value:
            raise SupplierOrderQuantityError("Количество меньше минимума заказа.")
        if not is_decimal_multiple(quantity.value, self.order_multiple.value):
            raise SupplierOrderQuantityError(
                "Количество должно быть кратно коммерческому шагу от нуля."
            )

    def _with_changes(self, **changes: object) -> Self:
        """Проверяет новый экземпляр и сохраняет исходное предложение."""
        offer = replace(self, **changes)
        offer._validate()
        return offer

    def _validate(self) -> None:
        """Проверяет типы собственных полей, цену, приоритет и активность."""
        if (
            not isinstance(self.id, SupplierOfferIdVO)
            or not isinstance(self.supplier, SupplierReferenceVO)
            or not isinstance(self.inventory_item_id, SupplierInventoryItemIdVO)
            or not isinstance(self.supplier_sku, SupplierSkuVO)
            or not isinstance(self.base_uom, SupplierOfferUomCodeVO)
            or (
                self.price_list_id is not None
                and not isinstance(self.price_list_id, SupplierPriceListIdVO)
            )
            or (
                self.source_id is not None
                and not isinstance(self.source_id, SupplierSourceIdVO)
            )
            or not isinstance(self.min_order_qty, SupplierOrderQuantityVO)
            or not isinstance(self.order_multiple, SupplierOrderQuantityVO)
            or not isinstance(self.lead_time, SupplierLeadTimeVO)
            or type(self.priority) is not int
            or self.priority < 0
            or type(self.is_active) is not bool
        ):
            raise InvalidSupplierOfferValueError(
                "Нужны типизированные поля предложения, неотрицательный приоритет и bool активности."
            )
        if (
            not isinstance(self.purchase_price, MoneyVO)
            or not isinstance(self.purchase_price.amount, Decimal)
            or not self.purchase_price.amount.is_finite()
            or self.purchase_price.amount < 0
        ):
            raise InvalidSupplierOfferValueError(
                "Закупочная цена должна быть неотрицательной суммой MoneyVO."
            )
