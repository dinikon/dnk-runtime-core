from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class CreateContactCommand:
    last_name: str
    first_name: str
    middle_name: str | None = None
    tenant_id: UUID | None = None
    custom_fields: dict[str, object | None] | None = None


@dataclass(frozen=True, slots=True)
class UpdateContactCommand:
    contact_id: UUID
    last_name: str
    first_name: str
    middle_name: str | None = None
    tenant_id: UUID | None = None
    custom_fields: dict[str, object | None] | None = None


@dataclass(frozen=True, slots=True)
class CreateCompanyCommand:
    last_name: str
    company_name: str
    tenant_id: UUID | None = None
    custom_fields: dict[str, object | None] | None = None


@dataclass(frozen=True, slots=True)
class UpdateCompanyCommand:
    company_id: UUID
    last_name: str
    company_name: str
    tenant_id: UUID | None = None
    custom_fields: dict[str, object | None] | None = None


@dataclass(frozen=True, slots=True)
class DeleteContactCommand:
    contact_id: UUID


@dataclass(frozen=True, slots=True)
class DeleteCompanyCommand:
    company_id: UUID


__all__ = [
    "CreateCompanyCommand",
    "CreateContactCommand",
    "DeleteCompanyCommand",
    "DeleteContactCommand",
    "UpdateCompanyCommand",
    "UpdateContactCommand",
]
