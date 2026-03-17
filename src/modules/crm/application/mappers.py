from __future__ import annotations

from src.modules.crm.application.dto import CompanyDTO, ContactDTO
from src.modules.crm.domain.entities import CompanyEntity, ContactEntity


def contact_to_dto(
    contact: ContactEntity,
    *,
    custom_fields: dict[str, object | None] | None = None,
) -> ContactDTO:
    return ContactDTO(
        id=contact.id,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
        last_name=contact.last_name,
        first_name=contact.first_name,
        middle_name=contact.middle_name,
        custom_fields=dict(custom_fields or {}),
    )


def company_to_dto(
    company: CompanyEntity,
    *,
    custom_fields: dict[str, object | None] | None = None,
) -> CompanyDTO:
    return CompanyDTO(
        id=company.id,
        created_at=company.created_at,
        updated_at=company.updated_at,
        last_name=company.last_name,
        company_name=company.company_name,
        custom_fields=dict(custom_fields or {}),
    )


__all__ = [
    "company_to_dto",
    "contact_to_dto",
]
