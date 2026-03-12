from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.modules.crm.domain.contact.entity import ContactEntity


@dataclass(frozen=True, slots=True)
class GetContactRecordQuery:
    tenant_id: UUID
    contact_id: UUID


@dataclass(frozen=True, slots=True)
class ContactRecord:
    contact: ContactEntity
    custom_fields: dict[str, object]


class ContactRecordRepositoryPort(Protocol):
    async def get_by_id(
        self,
        query: GetContactRecordQuery,
    ) -> ContactRecord | None: ...


__all__ = [
    "ContactRecord",
    "ContactRecordRepositoryPort",
    "GetContactRecordQuery",
]
