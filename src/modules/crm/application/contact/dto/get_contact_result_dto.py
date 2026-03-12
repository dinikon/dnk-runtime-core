from __future__ import annotations

from dataclasses import dataclass

from src.modules.crm.domain.contact.entity import ContactEntity


@dataclass(frozen=True, slots=True)
class GetContactResultDTO:
    contact: ContactEntity
    custom_fields: dict[str, object]


__all__ = ["GetContactResultDTO"]
