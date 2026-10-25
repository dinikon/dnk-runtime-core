from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class BasketItemResponse(BaseModel):
    """Неизменяемое транспортное представление сохранённой строки."""

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


class OwnerBasketResponse(BaseModel):
    """Сохранённая корзина в ответе сценария владельца."""

    id: UUID
    currency: str
    revision: int
    state: str
    total: str
    items: tuple[BasketItemResponse, ...]


class BasketSummaryResponse(BaseModel):
    """Точная сумма строки списка."""

    currency: str
    total: str
    revision: int


class PointResponse(BaseModel):
    """Собственная точка связи и идентификаторы binding."""

    binding_id: UUID
    contact_point_id: UUID
    type: str
    value: str
    country_code: str | None
    label_id: UUID | None
    position: int


class PointsResponse(BaseModel):
    """Два типизированных набора связи."""

    phones: tuple[PointResponse, ...]
    emails: tuple[PointResponse, ...]
