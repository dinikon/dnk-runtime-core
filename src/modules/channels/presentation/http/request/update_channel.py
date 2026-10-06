from pydantic import BaseModel, ConfigDict, Field, model_validator


class UpdateChannelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, hide_input_in_errors=True)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    is_active: bool | None = None
    config_version: int | None = Field(default=None, ge=1)
    connection_settings: dict[str, str] | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def valid_patch(self):
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
