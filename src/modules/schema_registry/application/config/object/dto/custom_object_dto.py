from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from src.modules.schema_registry.application.config.field.dto import CustomFieldDTO


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


__all__ = ["CustomObjectDTO"]
