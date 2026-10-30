"""Желаемое наличие и возможности адресата без знаний о площадках."""

from dataclasses import dataclass
from enum import StrEnum

from src.modules.channels.domain.stock_sync.error import StockSyncError
from src.modules.channels.domain.types import JsonObject


class StockMode(StrEnum):
    """Собственное количество, ручное наличие или наследование."""

    QUANTITY = "quantity"
    AVAILABILITY = "availability"
    INHERIT = "inherit"


@dataclass(frozen=True, slots=True)
class DesiredStockVO:
    """Хранит режим и уже разрешённые Catalog эффективные значения."""

    mode: StockMode
    quantity: int | None
    availability: str
    backorders: str = "no"

    def __post_init__(self) -> None:
        """Не смешивает неизвестное количество с нулём или ручным наличием."""
        if (
            not isinstance(self.mode, StockMode)
            or not isinstance(self.availability, str)
            or self.availability not in {"in_stock", "out_of_stock", "on_order"}
            or not isinstance(self.backorders, str)
            or self.backorders not in {"no", "notify", "yes"}
            or (
                self.quantity is not None
                and (
                    type(self.quantity) is not int
                    or not -2147483648 <= self.quantity <= 2147483647
                )
            )
            or (
                self.mode is StockMode.AVAILABILITY
                and (self.quantity is not None or self.backorders != "no")
            )
            or (self.mode is not StockMode.AVAILABILITY and self.quantity is None)
        ):
            raise StockSyncError("stock_state_invalid")

    def to_document(self) -> JsonObject:
        """Сериализует конкретное версионированное значение."""
        return {
            "version": 1,
            "mode": self.mode.value,
            "quantity": self.quantity,
            "availability": self.availability,
            "backorders": self.backorders,
        }


@dataclass(frozen=True, slots=True)
class StockFeaturesVO:
    """Нормализованные возможности нативного API, объявленные его адаптером."""

    inheritance: bool = False
    manual_availability: tuple[str, ...] = ()
    backorders: tuple[str, ...] = ("no",)

    def warning(self, desired: DesiredStockVO) -> str | None:
        """Определяет возможность записи без названия платформы и без сети."""
        if desired.quantity is not None and desired.quantity < 0:
            return "stock_negative_unsupported"
        if desired.mode is StockMode.AVAILABILITY:
            if desired.availability not in self.manual_availability:
                return "stock_status_unsupported"
        elif desired.backorders not in self.backorders:
            return "stock_backorders_unsupported"
        return None
