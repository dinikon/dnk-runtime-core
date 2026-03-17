from __future__ import annotations

from src.modules.crm.domain.entities import CompanyEntity, ContactEntity
from src.modules.crm.infrastructure.persistence.company import CompanyModel
from src.modules.crm.infrastructure.persistence.contact import ContactModel


def contact_to_model(contact: ContactEntity) -> ContactModel:
    return ContactModel(
        id=contact.id,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
        last_name=contact.last_name,
        first_name=contact.first_name,
        middle_name=contact.middle_name,
    )


def contact_model_to_entity(model: ContactModel) -> ContactEntity:
    return ContactEntity(
        id=model.id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        last_name=model.last_name,
        first_name=model.first_name,
        middle_name=model.middle_name,
    )


def company_to_model(company: CompanyEntity) -> CompanyModel:
    return CompanyModel(
        id=company.id,
        created_at=company.created_at,
        updated_at=company.updated_at,
        last_name=company.last_name,
        company_name=company.company_name,
    )


def company_model_to_entity(model: CompanyModel) -> CompanyEntity:
    return CompanyEntity(
        id=model.id,
        created_at=model.created_at,
        updated_at=model.updated_at,
        last_name=model.last_name,
        company_name=model.company_name,
    )


__all__ = [
    "company_model_to_entity",
    "company_to_model",
    "contact_model_to_entity",
    "contact_to_model",
]
