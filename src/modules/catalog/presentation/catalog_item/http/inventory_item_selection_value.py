from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr

from src.modules.catalog.application.catalog_item.inventory_item_selection import (
    CatalogInventoryItemSelection,
)


class ExistingInventoryItemValue(BaseModel):
    """Принимает только явный выбор существующей складской позиции."""

    model_config = ConfigDict(extra="forbid")
    mode: Literal["existing"]
    inventory_item_id: UUID


class NewInventoryItemValue(BaseModel):
    """Принимает ручной код для создания либо повторного использования SKU."""

    model_config = ConfigDict(extra="forbid")
    mode: Literal["create"]
    sku: StrictStr


class ClearInventoryItemValue(BaseModel):
    """Описывает явное снятие связи без удаления складской позиции."""

    model_config = ConfigDict(extra="forbid")
    mode: Literal["clear"]


InventoryItemSelectionValue = Annotated[
    ExistingInventoryItemValue | NewInventoryItemValue | ClearInventoryItemValue,
    Field(discriminator="mode"),
]


def inventory_item_selection(
    value: InventoryItemSelectionValue | None,
) -> CatalogInventoryItemSelection | None:
    """Явно переводит транспортный выбор в конкретный Application-вход."""
    if value is None:
        return None
    if isinstance(value, ExistingInventoryItemValue):
        return CatalogInventoryItemSelection(
            "existing", inventory_item_id=value.inventory_item_id
        )
    if isinstance(value, NewInventoryItemValue):
        return CatalogInventoryItemSelection("create", sku=value.sku)
    return CatalogInventoryItemSelection("clear")
