from dataclasses import dataclass
from enum import StrEnum
from src.modules.catalog.domain.error import InvalidCatalogValueError


class StockManagement(StrEnum):
    """Способ использования заявленного наличия карточки."""

    NONE = "none"
    OWN = "own"
    PARENT = "parent"


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
    """Один источник наличия либо ссылка на общий источник родителя."""

    manage_stock: StockManagement
    stock_quantity: int | None = None
    stock_status: StockStatus | None = None
    backorders: BackorderPolicy | None = None

    def __post_init__(self) -> None:
        """Запрещает смешивание локальных полей и режима общего источника."""
        if not isinstance(self.manage_stock, StockManagement):
            raise InvalidCatalogValueError("Некорректный режим наличия.")
        if self.manage_stock == StockManagement.PARENT:
            if any(
                v is not None
                for v in (self.stock_quantity, self.stock_status, self.backorders)
            ):
                raise InvalidCatalogValueError(
                    "Parent не имеет собственных полей наличия."
                )
        elif not isinstance(self.backorders, BackorderPolicy):
            raise InvalidCatalogValueError("Нужна политика предзаказа.")
        elif self.manage_stock == StockManagement.OWN:
            if (
                type(self.stock_quantity) is not int
                or self.stock_quantity < 0
                or self.stock_status is not None
            ):
                raise InvalidCatalogValueError(
                    "Own требует неотрицательное количество и вычисляемый статус."
                )
        elif self.stock_quantity is not None or not isinstance(
            self.stock_status, StockStatus
        ):
            raise InvalidCatalogValueError("None требует статус без количества.")
        elif (
            self.stock_status == StockStatus.ON_BACKORDER
            and self.backorders == BackorderPolicy.NO
        ):
            raise InvalidCatalogValueError("Предзаказ должен быть разрешён.")

    def effective_status(self) -> StockStatus | None:
        """Вычисляет статус собственного источника; parent разрешается политикой семьи."""
        if self.manage_stock == StockManagement.PARENT:
            return None
        if self.manage_stock == StockManagement.NONE:
            return self.stock_status
        if self.stock_quantity > 0:
            return StockStatus.IN_STOCK
        return (
            StockStatus.OUT_OF_STOCK
            if self.backorders == BackorderPolicy.NO
            else StockStatus.ON_BACKORDER
        )
