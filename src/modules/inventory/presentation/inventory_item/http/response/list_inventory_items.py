from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import BaseModel

from src.modules.inventory.application.inventory_item.query.list_inventory_items.dto import (
    ListInventoryItemsResultDTO,
)
from src.modules.inventory.domain.inventory_item.value_object.expiration_mode import (
    ExpirationMode,
)
from src.modules.inventory.domain.inventory_item.value_object.tracking_mode import (
    TrackingMode,
)


class ListInventoryItemQuantityRulesResponse(BaseModel):
    """Передаёт точный шаг количества строки списка."""

    step: Decimal


class ListInventoryItemResponse(BaseModel):
    """Описывает строку HTTP-списка без дочерних коллекций."""

    id: UUID
    sku: str
    base_uom: str
    quantity_rules: ListInventoryItemQuantityRulesResponse
    tracking_mode: TrackingMode
    expiration_mode: ExpirationMode


class ListInventoryItemsResponse(BaseModel):
    """Описывает страницу HTTP-списка и параметры пагинации."""

    items: tuple[ListInventoryItemResponse, ...]
    total: int
    offset: int
    limit: int

    @classmethod
    def from_dto(cls, dto: ListInventoryItemsResultDTO) -> Self:
        """Явно переводит проекции Application в контракт GET."""
        return cls(
            items=tuple(
                ListInventoryItemResponse(
                    id=item.id,
                    sku=item.sku,
                    base_uom=item.base_uom,
                    quantity_rules=ListInventoryItemQuantityRulesResponse(
                        step=item.quantity_step
                    ),
                    tracking_mode=item.tracking_mode,
                    expiration_mode=item.expiration_mode,
                )
                for item in dto.items
            ),
            total=dto.total,
            offset=dto.offset,
            limit=dto.limit,
        )
