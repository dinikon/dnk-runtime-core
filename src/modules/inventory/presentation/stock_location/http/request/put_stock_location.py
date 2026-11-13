from pydantic import BaseModel, ConfigDict, StrictBool, StrictStr


class PutStockLocationRequest(BaseModel):
    """Требует полное редактируемое представление без изменения принадлежности и типа."""

    model_config = ConfigDict(extra="forbid")
    code: StrictStr
    name: StrictStr
    is_active: StrictBool
