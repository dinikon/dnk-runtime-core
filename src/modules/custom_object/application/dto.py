from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping
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


@dataclass(frozen=True, slots=True)
class CustomObjectDTO:
    """DTO описания кастомного объекта и его полей."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    singular_name: str
    plural_name: str
    singular_label: str
    plural_label: str
    description: str
    kind: str
    fields: tuple[CustomFieldDTO, ...]


@dataclass(frozen=True, slots=True)
class CustomRecordDTO:
    """DTO runtime-записи кастомного объекта."""

    object_id: UUID
    row_id: UUID
    values: Mapping[str, Any]
