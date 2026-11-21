from src.modules.inventory.domain.value_object.stock_status import StockStatus
from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, StrictStr
from uuid import UUID


class CreateStatusChangeDraftLineRequest(BaseModel):
    """Проверяет форму исходного количества, не подменяя доменную проверку шага."""

    model_config = ConfigDict(extra="forbid")
    inventory_item_id: UUID
    quantity: Annotated[
        StrictStr,
        Field(max_length=128, pattern=r"^-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$"),
    ]
    uom: Annotated[StrictStr, Field(min_length=1, max_length=16)]


class CreateStatusChangeDraftRequest(BaseModel):
    """Принимает только склад, компанию-владельца и плановые строки."""

    model_config = ConfigDict(extra="forbid")
    warehouse_id: UUID
    owner_id: UUID
    target_status: StockStatus
    reason: Annotated[StrictStr, Field(min_length=1, max_length=1000)]
    lines: list[CreateStatusChangeDraftLineRequest] = Field(
        default_factory=list, max_length=100
    )
