from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType


class PublicationFieldResponse(BaseModel):
    """Передаёт состояние, настройки и диагностику одного поля."""

    model_config = ConfigDict(from_attributes=True)

    field_id: UUID
    label: str
    kind: FieldValueType
    required: bool
    min_value: int | None
    max_value: int | None
    min_length: int | None
    max_length: int | None
    min_amount: str | None
    max_amount: str | None
    currency: str | None
    has_override: bool
    override_value: str | int | bool | None
    original_value: str | int | bool | None
    resolved_value: str | int | bool | None
    original_issues: tuple[str, ...]
    issues: tuple[str, ...]


class GetPublicationFieldsResponse(BaseModel):
    """Возвращает карточку редактирования всех полей сохранённой схемы."""

    model_config = ConfigDict(from_attributes=True)

    feed_version: int
    publication_version: int
    readonly: bool
    source_available: bool
    fields: tuple[PublicationFieldResponse, ...]
