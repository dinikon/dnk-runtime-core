from uuid import UUID
from pydantic import BaseModel, ConfigDict, StrictStr


class PutStockSerialRequest(BaseModel):
    """Требует полный номер и явную связь с партией, разрешая null для очищения."""

    model_config = ConfigDict(extra="forbid")
    number: StrictStr
    lot_id: UUID | None
