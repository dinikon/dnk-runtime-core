from pydantic import BaseModel, ConfigDict, StrictStr


class AddTenantLocaleRequest(BaseModel):
    """Пользователь выбирает только код системной локали."""

    model_config = ConfigDict(extra="forbid")

    code: StrictStr
