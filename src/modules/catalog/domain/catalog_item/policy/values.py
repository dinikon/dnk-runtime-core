from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from src.modules.catalog.domain.catalog_item.value_object.snapshot import (
    CatalogItemValuesSnapshot,
)
from src.modules.catalog.domain.catalog_item.value_object.status import (
    CatalogItemStatus,
)
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    StockStatus,
    BackorderPolicy,
)


@dataclass(frozen=True, slots=True)
class CatalogItemComputedValues:
    """Вычисляемые значения самостоятельной продаваемой позиции."""

    price: Decimal | None
    stock_status: StockStatus
    backorders_allowed: bool
    backordered: bool
    available_for_sale: bool
    available_for_publication: bool


class CatalogItemValuesPolicy:
    """Вычисляет цену, наличие и доступность без I/O и системных часов."""

    @staticmethod
    def calculate(
        item: CatalogItemValuesSnapshot, as_of: datetime
    ) -> CatalogItemComputedValues:
        """Применяет интервал скидки и настройки наличия к собственным значениям."""
        status = item.stock.effective_status()
        active = item.status == CatalogItemStatus.ACTIVE
        return CatalogItemComputedValues(
            price=item.price.at(as_of) if item.price is not None else None,
            stock_status=status,
            backorders_allowed=item.stock.backorders != BackorderPolicy.NO,
            backordered=status == StockStatus.ON_BACKORDER,
            available_for_sale=active
            and item.price is not None
            and status != StockStatus.OUT_OF_STOCK,
            available_for_publication=active,
        )
