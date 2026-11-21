from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, StrictStr
from uuid import UUID


class CreateInternalMoveDraftLineRequest(BaseModel):
    """Проверяет форму исходного количества, не подменяя доменную проверку шага."""

    model_config = ConfigDict(extra="forbid")
    inventory_item_id: UUID
    quantity: Annotated[
        StrictStr,
        Field(max_length=128, pattern=r"^-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$"),
    ]
    uom: Annotated[StrictStr, Field(min_length=1, max_length=16)]


class CreateInternalMoveDraftRequest(BaseModel):
    """Принимает только склад, компанию-владельца и плановые строки."""

    model_config = ConfigDict(extra="forbid")
    warehouse_id: UUID
    owner_id: UUID
    lines: list[CreateInternalMoveDraftLineRequest] = Field(
        default_factory=list, max_length=100
    )
