from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.modules.channels.domain.types import JsonObject
from src.modules.channels.presentation.http.request.config import (
    ConnectionConfigRequest,
)


class UpdateChannelRequest(BaseModel):
    """PATCH различает отсутствие credentials и полный новый комплект."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    expected_revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    config: ConnectionConfigRequest | None = None
    credentials: JsonObject | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def require_present_values(self) -> Self:
        """Запрещает явный null вместо замены или сохранения текущего значения."""
        if any(
            getattr(self, key) is None
            for key in self.model_fields_set - {"expected_revision"}
        ):
            raise ValueError("null_not_allowed")
        return self
