from pydantic import BaseModel, ConfigDict, Field


class PutVariantContentRequest(BaseModel):
    """Тело HTTP-сценария put_variant_content; лишние поля отвергаются."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    expected_schema_version: int = Field(ge=1)
    values: dict[str, str]
