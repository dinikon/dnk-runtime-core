from __future__ import annotations

from dataclasses import dataclass

from src.modules.crm.application.contact.dto.contact_dto import ContactDTO


@dataclass(frozen=True, slots=True)
class ContactListResultDTO:
    """DTO страницы CRM-контактов с total count."""

    items: tuple[ContactDTO, ...]
    total: int
    limit: int
    offset: int


__all__ = ["ContactListResultDTO"]
