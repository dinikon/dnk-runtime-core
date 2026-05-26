from __future__ import annotations

from dataclasses import dataclass

from src.modules.contact_point.application.selection.strategy import (
    ContactPointSelectionStrategy,
)
from src.modules.contact_point.domain.contact_point import ContactPointIdVO
from src.modules.shared import EntityIdVO


@dataclass(frozen=True, slots=True)
class ContactPointSelectionCommand:
    tenant_id: EntityIdVO
    owner_object_id: EntityIdVO
    owner_record_id: EntityIdVO
    channel_code: str
    strategy: ContactPointSelectionStrategy = ContactPointSelectionStrategy.PRIMARY
    explicit_contact_point_id: ContactPointIdVO | None = None


__all__ = ["ContactPointSelectionCommand"]
