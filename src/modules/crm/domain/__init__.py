from src.modules.crm.domain.entities import CompanyEntity, ContactEntity
from src.modules.crm.domain.errors import (
    CompanyNotFoundError,
    ContactNotFoundError,
    InvalidCompanyLastNameError,
    InvalidCompanyNameError,
    InvalidContactFirstNameError,
    InvalidContactLastNameError,
    InvalidContactMiddleNameError,
)
from src.modules.crm.domain.repositories import (
    CompanyRepositoryProtocol,
    ContactRepositoryProtocol,
)
from src.modules.crm.domain.value_objects import CRM_TEXT_MAX_LENGTH

__all__ = [
    "CRM_TEXT_MAX_LENGTH",
    "CompanyEntity",
    "CompanyNotFoundError",
    "CompanyRepositoryProtocol",
    "ContactEntity",
    "ContactNotFoundError",
    "ContactRepositoryProtocol",
    "InvalidCompanyLastNameError",
    "InvalidCompanyNameError",
    "InvalidContactFirstNameError",
    "InvalidContactLastNameError",
    "InvalidContactMiddleNameError",
]
