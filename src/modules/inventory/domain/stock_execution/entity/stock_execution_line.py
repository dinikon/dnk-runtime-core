from dataclasses import dataclass
from decimal import Decimal
from typing import Self

from src.modules.inventory.domain.error import StockAdjustmentError
from src.modules.inventory.domain.stock_execution.value_object.adjustment_route import (
    StockAdjustmentExecutionRouteVO,
)

from src.modules.inventory.domain.error import (
    IncompatibleUomError,
    QuantityConversionMismatchError,
)
from src.modules.inventory.domain.inventory_item.error import (
    InvalidInventoryItemExecutionSnapshotError,
)
from src.modules.inventory.domain.inventory_item.execution_snapshot import (
    InventoryItemExecutionSnapshot,
)
from src.modules.inventory.domain.inventory_item.value_object.identifier import (
    InventoryItemIdVO,
)
from src.modules.inventory.domain.policy.quantity_validation import (
    QuantityValidationPolicy,
)
from src.modules.inventory.domain.policy.uom_conversion import UomConversionPolicy
from src.modules.inventory.domain.stock_document.value_object.line_id import (
    StockDocumentLineIdVO,
)
from src.modules.inventory.domain.stock_execution.error import (
    InvalidStockExecutionContextError,
    InvalidStockExecutionLineError,
)
from src.modules.inventory.domain.stock_execution.value_object.internal_move_route import (
    InternalMoveExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.issue_route import (
    IssueExecutionRouteVO,
)
from src.modules.inventory.domain.stock_execution.value_object.line_id import (
    StockExecutionLineIdVO,
)
from src.modules.inventory.domain.stock_execution.value_object.receipt_route import (
    ReceiptExecutionRouteVO,
)
from src.modules.inventory.domain.uom_catalog import get_uom
from src.modules.inventory.domain.value_object.quantity import QuantityVO
from src.modules.inventory.domain.value_object.quantity_conversion_snapshot import (
    QuantityConversionSnapshotVO,
)
from src.modules.inventory.domain.value_object.uom_code import UomCodeVO


@dataclass(frozen=True, slots=True)
class StockExecutionLine:
    """Фактическое положительное количество по плановой строке и конкретному физическому маршруту."""

    id: StockExecutionLineIdVO
    document_line_id: StockDocumentLineIdVO
    inventory_item_id: InventoryItemIdVO
    base_uom: UomCodeVO
    quantity: QuantityVO
    conversion: QuantityConversionSnapshotVO
    route: (
        ReceiptExecutionRouteVO
        | IssueExecutionRouteVO
        | InternalMoveExecutionRouteVO
        | StockAdjustmentExecutionRouteVO
    )

    @classmethod
    def create(
        cls,
        *,
        identifier: StockExecutionLineIdVO,
        document_line_id: StockDocumentLineIdVO,
        inventory_item: InventoryItemExecutionSnapshot,
        quantity: QuantityVO,
        uom: UomCodeVO,
        route: (
            ReceiptExecutionRouteVO
            | IssueExecutionRouteVO
            | InternalMoveExecutionRouteVO
            | StockAdjustmentExecutionRouteVO
        ),
    ) -> Self:
        """Фиксирует исходный пересчёт и вычисляет базовое количество по правилам товара."""
        if not isinstance(inventory_item, InventoryItemExecutionSnapshot):
            raise InvalidInventoryItemExecutionSnapshotError(
                "Нужен снимок правил исполнения товара."
            )
        inventory_item.ensure_valid()
        conversion = QuantityConversionSnapshotVO.create(
            quantity=quantity, uom=uom, base_uom=inventory_item.base_uom
        )
        line = cls.restore(
            identifier=identifier,
            document_line_id=document_line_id,
            inventory_item_id=inventory_item.inventory_item_id,
            base_uom=inventory_item.base_uom,
            quantity=conversion.to_base_quantity(),
            conversion=conversion,
            route=route,
        )
        line.ensure_compatible(inventory_item)
        return line

    @classmethod
    def restore(
        cls,
        *,
        identifier: StockExecutionLineIdVO,
        document_line_id: StockDocumentLineIdVO,
        inventory_item_id: InventoryItemIdVO,
        base_uom: UomCodeVO,
        quantity: QuantityVO,
        conversion: QuantityConversionSnapshotVO,
        route: (
            ReceiptExecutionRouteVO
            | IssueExecutionRouteVO
            | InternalMoveExecutionRouteVO
            | StockAdjustmentExecutionRouteVO
        ),
    ) -> Self:
        """Восстанавливает полный собственный состав и исторический пересчёт без текущих настроек."""
        line = cls(
            identifier,
            document_line_id,
            inventory_item_id,
            base_uom,
            quantity,
            conversion,
            route,
        )
        line.ensure_valid()
        return line

    def ensure_valid(self) -> None:
        """Проверяет собственные ссылки, положительность, маршрут и единичность серийного экземпляра."""
        if (
            not isinstance(self.id, StockExecutionLineIdVO)
            or not isinstance(self.document_line_id, StockDocumentLineIdVO)
            or not isinstance(self.inventory_item_id, InventoryItemIdVO)
            or not isinstance(self.base_uom, UomCodeVO)
            or not isinstance(self.quantity, QuantityVO)
            or self.quantity.value.is_zero()
            or not isinstance(self.conversion, QuantityConversionSnapshotVO)
            or not isinstance(
                self.route,
                (
                    ReceiptExecutionRouteVO,
                    IssueExecutionRouteVO,
                    InternalMoveExecutionRouteVO,
                    StockAdjustmentExecutionRouteVO,
                ),
            )
        ):
            raise InvalidStockExecutionLineError(
                "Нужны типизированные ссылки, маршрут и положительное фактическое количество."
            )
        if (
            get_uom(self.base_uom).dimension
            is not get_uom(self.conversion.uom).dimension
        ):
            raise IncompatibleUomError(
                "Исходная и базовая единицы исполнения должны иметь одну размерность."
            )
        if self.quantity != self.conversion.to_base_quantity():
            raise QuantityConversionMismatchError(
                "Фактическое количество не равно сохранённому пересчёту."
            )
        if isinstance(self.route, StockAdjustmentExecutionRouteVO) and (
            self.quantity.value != self.route.adjustment.quantity_delta.value.copy_abs()
            or self.conversion.uom != self.base_uom
            or self.conversion.factor_to_base != Decimal(1)
        ):
            raise StockAdjustmentError(
                "Фактическая корректировка требует точный модуль дельты и пересчёт 1:1 в базовой единице."
            )
        for dimensions in self.route.dimensions:
            if dimensions.inventory_item_id != self.inventory_item_id:
                raise InvalidStockExecutionLineError(
                    "Маршрут относится к другому товару."
                )
            if dimensions.serial_id is not None and (
                self.base_uom != UomCodeVO("PCS") or self.quantity.value != Decimal(1)
            ):
                raise InvalidStockExecutionLineError(
                    "Конкретный серийный экземпляр исполняется в количестве 1 PCS."
                )

    def ensure_compatible(self, inventory_item: InventoryItemExecutionSnapshot) -> None:
        """Повторно проверяет текущие единицу, коэффициент пересчёта и шаг количества."""
        self.ensure_valid()
        if isinstance(self.route, StockAdjustmentExecutionRouteVO):
            raise StockAdjustmentError(
                "Корректировку создаёт специализированная фабрика по полному плану и основанию."
            )
        if not isinstance(inventory_item, InventoryItemExecutionSnapshot):
            raise InvalidInventoryItemExecutionSnapshotError(
                "Нужен снимок правил исполнения товара."
            )
        inventory_item.ensure_valid()
        if (
            self.inventory_item_id != inventory_item.inventory_item_id
            or self.base_uom != inventory_item.base_uom
        ):
            raise InvalidStockExecutionContextError(
                "Товар и базовая единица исполнения должны совпадать с настройками."
            )
        factor = UomConversionPolicy.convert(
            quantity=QuantityVO(Decimal(1)),
            from_uom=self.conversion.uom,
            to_uom=self.base_uom,
        )
        if self.conversion.factor_to_base != factor.value:
            raise QuantityConversionMismatchError(
                "Новое исполнение требует текущего системного коэффициента."
            )
        QuantityValidationPolicy.validate(
            quantity=self.quantity, rules=inventory_item.quantity_rules
        )
