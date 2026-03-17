from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ContactDTO:
    id: UUID
    created_at: datetime
    updated_at: datetime
    last_name: str
    first_name: str
    middle_name: str | None
    custom_fields: dict[str, object | None] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CompanyDTO:
    id: UUID
    created_at: datetime
    updated_at: datetime
    last_name: str
    company_name: str
    custom_fields: dict[str, object | None] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DeleteContactResultDTO:
    contact_id: UUID
    deleted: bool


@dataclass(frozen=True, slots=True)
class DeleteCompanyResultDTO:
    company_id: UUID
    deleted: bool


__all__ = [
    "CompanyDTO",
    "ContactDTO",
    "DeleteCompanyResultDTO",
    "DeleteContactResultDTO",
]
