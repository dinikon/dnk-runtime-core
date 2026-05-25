from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from src.modules.contact_point.domain.contact_point import ContactPointTypeVO


@dataclass(frozen=True, slots=True)
class ContactPointSelectionDTO:
    contact_point_id: UUID
    contact_point_type: ContactPointTypeVO
    recipient_address: str
    recipient_snapshot: Mapping[str, Any]
    binding_id: UUID
    is_primary: bool


@dataclass(frozen=True, slots=True)
class ContactPointSelectionListDTO:
    items: tuple[ContactPointSelectionDTO, ...]
    count: int


__all__ = [
    "ContactPointSelectionDTO",
    "ContactPointSelectionListDTO",
]
