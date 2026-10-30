from pydantic import BaseModel, ConfigDict, Field, field_validator
from src.modules.channels.presentation.product_representation.http.request.fields import (
    RepresentationOverridesRequest,
)


class PreviewRepresentationRequest(BaseModel):
    """Позволяет выбрать подмножество настроенных локалей; по умолчанию читает все."""

    model_config = ConfigDict(extra="forbid")

    locales: tuple[str, ...] | None = Field(default=None, min_length=1, max_length=20)
    overrides: RepresentationOverridesRequest | None = None
    expected_revision: int | None = Field(default=None, ge=0, strict=True)
    expected_binding_revision: int | None = Field(default=None, ge=1, strict=True)
    expected_config_revision: int | None = Field(default=None, ge=1, strict=True)

    @field_validator("overrides")
    @classmethod
    def reject_explicit_null(
        cls, value: RepresentationOverridesRequest | None
    ) -> RepresentationOverridesRequest:
        """Отличает пропуск сохранённых overrides от явно переданного пустого черновика."""
        if value is None:
            raise ValueError("Для сброса передайте пустой документ overrides.")
        return value
