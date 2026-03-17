from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.modules.crm.domain.entities import CompanyEntity, ContactEntity


class ContactRepositoryProtocol(Protocol):
    async def add(self, contact: ContactEntity) -> None: ...
    async def update(self, contact: ContactEntity) -> None: ...
    async def get_by_id(self, contact_id: UUID) -> ContactEntity | None: ...


class CompanyRepositoryProtocol(Protocol):
    async def add(self, company: CompanyEntity) -> None: ...
    async def update(self, company: CompanyEntity) -> None: ...
    async def get_by_id(self, company_id: UUID) -> CompanyEntity | None: ...


__all__ = [
    "CompanyRepositoryProtocol",
    "ContactRepositoryProtocol",
]
