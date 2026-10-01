from pydantic import BaseModel, ConfigDict
from typing import Literal


class UpdateCurrentUserProfileRequestSchema(BaseModel):
    """Pydantic-схема обновления профиля текущего пользователя."""

    model_config = ConfigDict(extra="forbid")
    last_name: str
    first_name: str
    middle_name: str | None
    interface_language: Literal["uk", "en"]
    interface_theme: Literal["system", "dark", "light"]
    timezone: Literal["Europe/Kyiv", "Europe/Warsaw"]
