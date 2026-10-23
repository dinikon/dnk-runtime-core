from typing import Literal

from pydantic import BaseModel, model_validator


class CloudStartRequest(BaseModel):
    """Параметры запуска ручного или автоматического облачного входа."""

    purpose: Literal["login", "link"] = "login"
    silent: bool = False

    @model_validator(mode="after")
    def validate_silent_login(self) -> "CloudStartRequest":
        """Разрешает автоматическую попытку только для входа."""
        if self.silent and self.purpose != "login":
            raise ValueError("Silent authorization is only available for login.")
        return self
