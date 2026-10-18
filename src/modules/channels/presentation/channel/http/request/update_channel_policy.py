from typing import Self
from pydantic import BaseModel, ConfigDict, Field, model_validator


class UpdateChannelPolicyRequest(BaseModel):
    """Принимает поля HTTP-сценария update_channel_policy без tenant/actor из body."""

    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    revision: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    is_enabled: bool | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> Self:
        """Отклоняет пустой PATCH и явный null в non-nullable полях."""
        changed = self.model_fields_set - {"revision"}
        if not changed or any((getattr(self, key) is None for key in changed)):
            raise ValueError("Invalid or empty channel patch.")
        return self
