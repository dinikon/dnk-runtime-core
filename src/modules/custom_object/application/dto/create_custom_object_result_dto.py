from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateCustomObjectResultDTO:
    id: UUID
    object_name_singular: str
    object_name_plural: str
    object_label_singular: str
    object_label_plural: str
    description: str | None
    icon: str | None
    shortcut: str | None
    is_active: bool
    is_ui_read_only: bool
    created_at: datetime
    updated_at: datetime


__all__ = ["CreateCustomObjectResultDTO"]
