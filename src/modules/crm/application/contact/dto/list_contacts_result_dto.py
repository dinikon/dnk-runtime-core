from __future__ import annotations

from dataclasses import dataclass, field

from src.modules.crm.application.contact.dto.list_contact_item_dto import (
    ListContactItemDTO,
)


@dataclass(frozen=True, slots=True)
class ListContactsResultDTO:
    items: list[ListContactItemDTO] = field(default_factory=list)
    total: int | None = None


__all__ = ["ListContactsResultDTO"]
