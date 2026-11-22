from dataclasses import dataclass
from uuid import UUID

from src.modules.feed_builder.domain.feed.enum.field_value_type import FieldValueType


@dataclass(frozen=True, slots=True)
class PublicationFieldDTO:
    """Отображает правила, исходное и итоговое значения конкретного поля."""

    field_id: UUID
    label: str
    kind: FieldValueType
    required: bool
    min_length: int | None
    max_length: int | None
    min_amount: str | None
    max_amount: str | None
    currency: str | None
    has_override: bool
    override_value: str | None
    original_value: str | None
    resolved_value: str | None
    original_issues: tuple[str, ...]
    issues: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GetPublicationFieldsResultDTO:
    """Передаёт поля и версии, по которым пользователь редактирует публикацию."""

    feed_version: int
    publication_version: int
    readonly: bool
    source_available: bool
    fields: tuple[PublicationFieldDTO, ...]
