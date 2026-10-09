from pydantic import BaseModel, ConfigDict, Field


class PutProductTypeTranslationRequest(BaseModel):
    """Тело HTTP-сценария put_product_type_translation; лишние поля отвергаются."""

    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    label: str = Field(min_length=1, max_length=255)
