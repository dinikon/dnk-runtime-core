from typing import Annotated
from pydantic import BaseModel, ConfigDict, Field, StrictStr
from uuid import UUID


class CreateReturnDraftLineRequest(BaseModel):
    """Проверяет форму исходного количества, не подменяя доменную проверку шага."""

    model_config = ConfigDict(extra="forbid")
    origin_execution_line_id: UUID
    quantity: Annotated[
        StrictStr,
        Field(max_length=128, pattern=r"^-?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)$"),
    ]
    uom: Annotated[StrictStr, Field(min_length=1, max_length=16)]


class CreateReturnDraftRequest(BaseModel):
    """Принимает только склад, компанию-владельца и плановые строки."""

    model_config = ConfigDict(extra="forbid")
    origin_execution_id: UUID
    reason: Annotated[StrictStr, Field(min_length=1, max_length=1000)]
    lines: list[CreateReturnDraftLineRequest] = Field(
        default_factory=list, max_length=100
    )
