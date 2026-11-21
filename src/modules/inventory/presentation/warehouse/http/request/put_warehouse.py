from pydantic import BaseModel, ConfigDict, StrictBool, StrictStr


class PutWarehouseRequest(BaseModel):
    """Требует полное редактируемое представление склада без полей локации."""

    model_config = ConfigDict(extra="forbid")
    code: StrictStr
    name: StrictStr
    is_active: StrictBool
