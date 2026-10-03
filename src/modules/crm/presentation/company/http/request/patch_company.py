from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.json_schema import SkipJsonSchema


class PatchCompanyRequest(BaseModel):
    """Название необязательно в схеме PATCH, но пустое изменение запрещено."""

    model_config = ConfigDict(extra="forbid", strict=True)

    legal_name: str | SkipJsonSchema[None] = None

    @model_validator(mode="after")
    def require_changes(self) -> "PatchCompanyRequest":
        if "legal_name" not in self.model_fields_set:
            raise ValueError("At least one company field is required.")
        if self.legal_name is None:
            raise ValueError("legal_name must be a string when provided.")
        return self
