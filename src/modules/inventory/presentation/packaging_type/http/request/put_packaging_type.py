from pydantic import BaseModel, ConfigDict, StrictBool, StrictStr


class PutPackagingTypeRequest(BaseModel):
    """Требует полный набор кода, названия и строгой активности типа тары."""

    model_config = ConfigDict(extra="forbid")
    code: StrictStr
    name: StrictStr
    is_active: StrictBool
