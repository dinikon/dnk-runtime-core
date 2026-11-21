from pydantic import BaseModel, ConfigDict, StrictStr


class CreateWarehouseRequest(BaseModel):
    """Принимает только ручные код и название, без ID и настроек локации."""

    model_config = ConfigDict(extra="forbid")
    code: StrictStr
    name: StrictStr
