from pydantic import BaseModel, ConfigDict, StrictStr


class CreatePackagingTypeRequest(BaseModel):
    """Принимает только ручные код и название без ID и активности."""

    model_config = ConfigDict(extra="forbid")
    code: StrictStr
    name: StrictStr
