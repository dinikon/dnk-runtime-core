from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CustomFieldDTO:
    """DTO описания поля кастомного объекта."""

    id: UUID
    field_name: str
    label: str
    description: str
    type: str
    is_nullable: bool
    default_value: str | None
    options: dict[str, str]
    kind: str


__all__ = ["CustomFieldDTO"]
