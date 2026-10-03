from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.json_schema import SkipJsonSchema


class PatchContactRequest(BaseModel):
    """Только явно переданные части ФИО."""

    model_config = ConfigDict(extra="forbid", strict=True)

    first_name: str | SkipJsonSchema[None] = None
    last_name: str | None = None
    middle_name: str | None = None

    @model_validator(mode="after")
    def require_changes(self) -> "PatchContactRequest":
        if not self.model_fields_set:
            raise ValueError("At least one name field is required.")
        if "first_name" in self.model_fields_set and self.first_name is None:
            raise ValueError("first_name must be a string when provided.")
        return self
