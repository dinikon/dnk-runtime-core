from dataclasses import dataclass
from decimal import Decimal
from typing import Self
from enum import StrEnum
from src.modules.catalog.domain.error import InvalidCatalogValueError


class StockStatus(StrEnum):
    """Эффективное наличие без складских движений и резервов."""

    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    ON_BACKORDER = "on_backorder"


class BackorderPolicy(StrEnum):
    """Разрешение заказа при исчерпанном заявленном количестве."""

    NO = "no"
    NOTIFY = "notify"
    YES = "yes"


@dataclass(frozen=True, slots=True)
class StockSpecificationVO:
    """Собственные настройки количественного учёта или ручного наличия."""

    manage_stock: bool = False
    stock_quantity: int | None = None
    stock_status: StockStatus | None = StockStatus.IN_STOCK
    backorders: BackorderPolicy = BackorderPolicy.NO

    def __post_init__(self) -> None:
        """Проверяет согласованность собственного количества и ручного статуса."""
        if type(self.manage_stock) is not bool or not isinstance(
            self.backorders, BackorderPolicy
        ):
            raise InvalidCatalogValueError(
                "Нужны boolean manage_stock и политика предзаказа."
            )
        if self.manage_stock:
            if type(self.stock_quantity) is not int or self.stock_status is not None:
                raise InvalidCatalogValueError(
                    "Учёт требует целое количество и вычисляемый статус."
                )
            if not -2147483648 <= self.stock_quantity <= 2147483647:
                raise InvalidCatalogValueError(
                    "Количество вне поддерживаемого диапазона.", ("quantity",)
                )
        elif (
            self.stock_quantity is not None
            or self.backorders != BackorderPolicy.NO
            or not isinstance(self.stock_status, StockStatus)
        ):
            raise InvalidCatalogValueError(
                "Ручное наличие требует статус без количества и backorders=no."
            )

    @classmethod
    def from_declared_values(
        cls,
        manage_stock: bool,
        quantity: Decimal | None,
        status: str | None,
        backorders: str,
    ) -> Self:
        """Преобразует точное количество без округления и проверяет политику наличия."""
        if quantity is not None and (
            not quantity.is_finite() or quantity != quantity.to_integral_value()
        ):
            raise InvalidCatalogValueError(
                "Количество должно быть целым.", ("quantity",)
            )
        try:
            return cls(
                manage_stock,
                int(quantity) if quantity is not None else None,
                StockStatus(status) if status is not None else None,
                BackorderPolicy(backorders),
            )
        except ValueError as error:
            raise InvalidCatalogValueError(
                "Выберите корректную политику наличия.", ("stock",)
            ) from error

    def effective_status(self) -> StockStatus:
        """Вычисляет наличие собственного источника с порогом количества ноль."""
        if not self.manage_stock:
            return self.stock_status
        if self.stock_quantity > 0:
            return StockStatus.IN_STOCK
        return (
            StockStatus.OUT_OF_STOCK
            if self.backorders == BackorderPolicy.NO
            else StockStatus.ON_BACKORDER
        )
