"""Read projections never reconstruct aggregates."""

from datetime import datetime
from src.modules.crm.application.contact.dto import ContactDTO
from src.modules.crm.application.company.dto import CompanyDTO
from src.modules.crm.domain.contact.value_object import ContactIdVO
from src.modules.crm.domain.company.value_object import CompanyIdVO
from .base import checked, identifier


def audit_values(row):
    return dict(
        created_at=checked(row["created_at"], datetime),
        updated_at=checked(row["updated_at"], datetime),
        created_by=identifier(row["created_by"]),
        updated_by=identifier(row["updated_by"]),
    )


def contact_projection(row):
    return ContactDTO(
        id=identifier(row["id"], ContactIdVO),
        first_name=checked(row["first_name"], str),
        last_name=checked(row["last_name"], str, optional=True),
        middle_name=checked(row["middle_name"], str, optional=True),
        **audit_values(row),
    )


def company_projection(row):
    return CompanyDTO(
        id=identifier(row["id"], CompanyIdVO),
        name=checked(row["name"], str),
        **audit_values(row),
    )
