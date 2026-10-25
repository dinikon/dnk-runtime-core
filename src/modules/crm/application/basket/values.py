from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class BasketLineInput:
    """Явный кандидат коммерческой строки."""

    name: str
    kind: str
    quantity: Decimal
    unit_price: Decimal
    unit: str = "шт."
    id: UUID | None = None
    client_line_key: str | None = None
    catalog_item_id: UUID | None = None
    sku: str | None = None
    custom_fields: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BasketInput:
    """Полный кандидат корзины, не универсальный HTTP DTO."""

    currency: str
    items: tuple[BasketLineInput, ...] = ()
    expected_revision: int | None = None


@dataclass(frozen=True, slots=True)
class BasketItemProjection:
    """Точные значения сохранённой строки для чтения."""

    id: UUID
    name: str
    kind: str
    quantity: str
    unit_price: str
    line_total: str
    unit: str
    catalog_item_id: UUID | None
    sku: str | None
    custom_fields: dict[str, str]


@dataclass(frozen=True, slots=True)
class OwnerBasketProjection:
    """Публичный внутренний контракт чтения корзины владельца."""

    id: UUID
    currency: str
    revision: int
    state: str
    total: str
    items: tuple[BasketItemProjection, ...]


@dataclass(frozen=True, slots=True)
class BasketSummaryProjection:
    """Пакетная денежная сводка без восстановления агрегата."""

    currency: str
    total: str
    revision: int
