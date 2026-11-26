from dataclasses import dataclass
from uuid import UUID

from src.modules.feed_builder.domain.feed.types import ResolvedFieldValue


@dataclass(frozen=True, slots=True)
class FieldIssue:
    """Описывает ошибку значения поля или недоступность позиции."""

    field_id: UUID | None
    code: str
    message: str
    path: tuple[str | int, ...] = ()
    rule_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class ResolvedField:
    """Передаёт конечное типизированное значение и его происхождение."""

    field_id: UUID
    value: ResolvedFieldValue
    origin: str
    actual_locale: str | None = None
    issues: tuple[FieldIssue, ...] = ()
