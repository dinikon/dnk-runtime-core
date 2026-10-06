from typing import Self
from pydantic import BaseModel, ConfigDict, Field, model_validator


class UpdateChannelRequest(BaseModel):
    """Ограничивает входные поля HTTP-сценария update_channel; credentials скрыты из repr."""

    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)
    name: str | None = None
    is_active: bool | None = None
    config_version: int | None = Field(default=None, ge=1)
    connection_settings: dict[str, str] | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def valid_patch(self) -> Self:
        """Различает пропущенные поля и null; требует версию вместе с настройками."""
        if not self.model_fields_set or any(
            getattr(self, key) is None for key in self.model_fields_set
        ):
            raise ValueError("Patch must contain non-null fields.")
        if ("connection_settings" in self.model_fields_set) != (
            "config_version" in self.model_fields_set
        ):
            raise ValueError(
                "Settings and configuration version must be supplied together."
            )
        return self
