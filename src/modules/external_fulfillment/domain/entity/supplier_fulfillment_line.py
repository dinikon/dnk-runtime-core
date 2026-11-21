from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Self

from src.modules.external_fulfillment.domain.error import (
    InvalidSupplierFulfillmentValueError,
    SupplierFulfillmentBasisMismatchError,
)
from src.modules.external_fulfillment.domain.value_object.identifier import (
    SupplierFulfillmentLineIdVO,
)
from src.modules.external_fulfillment.domain.value_object.line_confirmation import (
    SupplierFulfillmentLineConfirmationVO,
)
from src.modules.external_fulfillment.domain.value_object.quantity import (
    SupplierFulfillmentQuantityVO,
)
from src.modules.external_fulfillment.domain.value_object.quantity_terms import (
    SupplierFulfillmentQuantityTermsVO,
)
from src.modules.external_fulfillment.domain.value_object.references import (
    ExternalFulfillmentAllocationIdVO,
    ExternalInventoryItemIdVO,
    ExternalSupplierOfferIdVO,
)
from src.modules.external_fulfillment.domain.value_object.uom_code import (
    SupplierFulfillmentUomCodeVO,
)
from src.modules.shared.domain.value_object.money import MoneyVO


@dataclass(frozen=True, slots=True)
class SupplierFulfillmentLine:
    """Фиксирует запрос по одному целому внешнему распределению."""

    id: SupplierFulfillmentLineIdVO
    fulfillment_allocation_id: ExternalFulfillmentAllocationIdVO
    inventory_item_id: ExternalInventoryItemIdVO
    supplier_offer_id: ExternalSupplierOfferIdVO
    base_uom: SupplierFulfillmentUomCodeVO
    requested_quantity: SupplierFulfillmentQuantityVO
    quoted_price: MoneyVO
    confirmed_quantity: SupplierFulfillmentQuantityVO | None = None
    confirmed_price: MoneyVO | None = None
    quantity_terms: SupplierFulfillmentQuantityTermsVO | None = None
    shipped_quantity: SupplierFulfillmentQuantityVO = SupplierFulfillmentQuantityVO(
        Decimal(0)
    )

    @classmethod
    def create(
        cls,
        *,
        identifier: SupplierFulfillmentLineIdVO,
        fulfillment_allocation_id: ExternalFulfillmentAllocationIdVO,
        inventory_item_id: ExternalInventoryItemIdVO,
        supplier_offer_id: ExternalSupplierOfferIdVO,
        base_uom: SupplierFulfillmentUomCodeVO,
        requested_quantity: SupplierFulfillmentQuantityVO,
        quoted_price: MoneyVO,
    ) -> Self:
        """Создаёт строку из согласованных ссылок, количества и цены распределения."""
        return cls.restore(
            identifier=identifier,
            fulfillment_allocation_id=fulfillment_allocation_id,
            inventory_item_id=inventory_item_id,
            supplier_offer_id=supplier_offer_id,
            base_uom=base_uom,
            requested_quantity=requested_quantity,
            quoted_price=quoted_price,
        )

    @classmethod
    def restore(
        cls,
        *,
        identifier: SupplierFulfillmentLineIdVO,
        fulfillment_allocation_id: ExternalFulfillmentAllocationIdVO,
        inventory_item_id: ExternalInventoryItemIdVO,
        supplier_offer_id: ExternalSupplierOfferIdVO,
        base_uom: SupplierFulfillmentUomCodeVO,
        requested_quantity: SupplierFulfillmentQuantityVO,
        quoted_price: MoneyVO,
        confirmed_quantity: SupplierFulfillmentQuantityVO | None = None,
        confirmed_price: MoneyVO | None = None,
        quantity_terms: SupplierFulfillmentQuantityTermsVO | None = None,
        shipped_quantity: SupplierFulfillmentQuantityVO = SupplierFulfillmentQuantityVO(
            Decimal(0)
        ),
    ) -> Self:
        """Восстанавливает собственные поля строки без текущего предложения."""
        line = cls(
            identifier,
            fulfillment_allocation_id,
            inventory_item_id,
            supplier_offer_id,
            base_uom,
            requested_quantity,
            quoted_price,
            confirmed_quantity,
            confirmed_price,
            quantity_terms,
            shipped_quantity,
        )
        line.ensure_valid()
        return line

    def confirm(self, confirmation: SupplierFulfillmentLineConfirmationVO) -> Self:
        """Фиксирует ответ по этой строке в пределах исходного запроса."""
        if not isinstance(confirmation, SupplierFulfillmentLineConfirmationVO):
            raise InvalidSupplierFulfillmentValueError(
                "Нужно подтверждение строки поставщика."
            )
        if confirmation.line_id != self.id or not self._accepts_confirmation(
            confirmation.quantity, confirmation.price
        ):
            raise SupplierFulfillmentBasisMismatchError(
                "Ответ должен соблюдать исходные количество, правила количества, цену и валюту строки."
            )
        return replace(
            self,
            confirmed_quantity=confirmation.quantity,
            confirmed_price=confirmation.price,
        )

    def ship(self, quantity: SupplierFulfillmentQuantityVO) -> Self:
        """Фиксирует полную отправку положительного подтверждённого количества."""
        if (
            not isinstance(quantity, SupplierFulfillmentQuantityVO)
            or quantity.value.is_zero()
            or quantity != self.confirmed_quantity
        ):
            raise SupplierFulfillmentBasisMismatchError(
                "Отправленное количество должно равняться подтверждённому."
            )
        return replace(self, shipped_quantity=quantity)

    def ensure_valid(self) -> None:
        """Проверяет ссылки строки, положительное запрошенное количество и цену."""
        if (
            not isinstance(self.id, SupplierFulfillmentLineIdVO)
            or not isinstance(
                self.fulfillment_allocation_id, ExternalFulfillmentAllocationIdVO
            )
            or not isinstance(self.inventory_item_id, ExternalInventoryItemIdVO)
            or not isinstance(self.supplier_offer_id, ExternalSupplierOfferIdVO)
            or not isinstance(self.base_uom, SupplierFulfillmentUomCodeVO)
            or not isinstance(self.requested_quantity, SupplierFulfillmentQuantityVO)
            or self.requested_quantity.value <= 0
            or not isinstance(self.quoted_price, MoneyVO)
            or not isinstance(self.quoted_price.amount, Decimal)
            or not self.quoted_price.amount.is_finite()
            or self.quoted_price.amount < 0
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Строка требует номинальные ссылки, положительное количество и неотрицательную цену."
            )
        if self.quantity_terms is not None and (
            not isinstance(self.quantity_terms, SupplierFulfillmentQuantityTermsVO)
            or not self.quantity_terms.accepts(self.requested_quantity)
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Запрошенное количество должно соответствовать сохранённым правилам."
            )
        if (
            self.confirmed_quantity is not None or self.confirmed_price is not None
        ) and not self._accepts_confirmation(
            self.confirmed_quantity, self.confirmed_price
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Ответ по строке должен соответствовать исходным условиям запроса."
            )
        if not isinstance(self.shipped_quantity, SupplierFulfillmentQuantityVO) or (
            not self.shipped_quantity.value.is_zero()
            and self.shipped_quantity != self.confirmed_quantity
        ):
            raise InvalidSupplierFulfillmentValueError(
                "Отгруженное количество должно быть нулевым или равняться подтверждённому."
            )

    def _accepts_confirmation(
        self, quantity: SupplierFulfillmentQuantityVO | None, price: MoneyVO | None
    ) -> bool:
        """Проверяет цену и применяет сохранённые правила при уменьшении количества."""
        if not isinstance(quantity, SupplierFulfillmentQuantityVO):
            return False
        if quantity.value.is_zero():
            return self.quantity_terms is not None and price is None
        if not isinstance(price, MoneyVO) or price != self.quoted_price:
            return False
        if quantity == self.requested_quantity:
            return True
        return (
            self.quantity_terms is not None
            and quantity.value < self.requested_quantity.value
            and self.quantity_terms.accepts(quantity)
        )
