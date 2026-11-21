from uuid import UUID
from pydantic import BaseModel, ConfigDict, StrictStr


class CreateStockSerialRequest(BaseModel):
    """Принимает только номер и необязательную ссылку на партию; даты запрещены."""

    model_config = ConfigDict(extra="forbid")
    number: StrictStr
    lot_id: UUID | None = None
