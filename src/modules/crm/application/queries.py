from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GetContactQuery:
    contact_id: UUID
    tenant_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class GetCompanyQuery:
    company_id: UUID
    tenant_id: UUID | None = None


__all__ = [
    "GetCompanyQuery",
    "GetContactQuery",
]
