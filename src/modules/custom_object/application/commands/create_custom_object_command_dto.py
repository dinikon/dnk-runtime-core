from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateCustomObjectCommandDTO:
    tenant_id: UUID
    object_name_singular: str
    object_name_plural: str | None = None
    object_label_singular: str | None = None
    object_label_plural: str | None = None
    description: str | None = None
    icon: str | None = None
    shortcut: str | None = None
    is_active: bool = True
    is_ui_read_only: bool = False


__all__ = ["CreateCustomObjectCommandDTO"]
