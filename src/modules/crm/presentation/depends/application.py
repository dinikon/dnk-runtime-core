from src.modules.crm.presentation.depends.infrastructure import CrmContactPointsDep
from typing import Annotated

from fastapi import Depends

from src.modules.crm.application.company.use_case import (
    CreateCompanyUseCase,
    DeleteCompanyUseCase,
    GetCompanyUseCase,
    ListCompaniesUseCase,
    UpdateCompanyUseCase,
)
from src.modules.crm.application.contact.use_case import (
    CreateContactUseCase,
    DeleteContactUseCase,
    GetContactUseCase,
    ListContactsUseCase,
    UpdateContactUseCase,
)
from src.modules.crm.presentation.depends.infrastructure import (
    CompanyRepositoryDep,
    ContactRepositoryDep,
)
from src.modules.shared.presentation.time.depends import ClockDep


def get_create_contact_use_case(
    repository: ContactRepositoryDep,
    clock: ClockDep,
    contact_points: CrmContactPointsDep,
):
    """Собирает CreateContactUseCase."""
    return CreateContactUseCase(repository, clock, contact_points)


def get_get_contact_use_case(
    repository: ContactRepositoryDep, contact_points: CrmContactPointsDep
):
    """Собирает GetContactUseCase."""
    return GetContactUseCase(repository, contact_points)


def get_list_contacts_use_case(
    repository: ContactRepositoryDep, contact_points: CrmContactPointsDep
):
    """Собирает ListContactsUseCase."""
    return ListContactsUseCase(repository, contact_points)


def get_update_contact_use_case(
    repository: ContactRepositoryDep,
    clock: ClockDep,
    contact_points: CrmContactPointsDep,
):
    """Собирает UpdateContactUseCase."""
    return UpdateContactUseCase(repository, clock, contact_points)


def get_delete_contact_use_case(
    repository: ContactRepositoryDep, contact_points: CrmContactPointsDep
):
    """Собирает DeleteContactUseCase."""
    return DeleteContactUseCase(repository, contact_points)


CreateContactUseCaseDep = Annotated[
    CreateContactUseCase, Depends(get_create_contact_use_case)
]
GetContactUseCaseDep = Annotated[GetContactUseCase, Depends(get_get_contact_use_case)]
ListContactsUseCaseDep = Annotated[
    ListContactsUseCase, Depends(get_list_contacts_use_case)
]
UpdateContactUseCaseDep = Annotated[
    UpdateContactUseCase, Depends(get_update_contact_use_case)
]
DeleteContactUseCaseDep = Annotated[
    DeleteContactUseCase, Depends(get_delete_contact_use_case)
]


def get_create_company_use_case(
    repository: CompanyRepositoryDep,
    clock: ClockDep,
    contact_points: CrmContactPointsDep,
):
    """Собирает CreateCompanyUseCase."""
    return CreateCompanyUseCase(repository, clock, contact_points)


def get_get_company_use_case(
    repository: CompanyRepositoryDep, contact_points: CrmContactPointsDep
):
    """Собирает GetCompanyUseCase."""
    return GetCompanyUseCase(repository, contact_points)


def get_list_companies_use_case(
    repository: CompanyRepositoryDep, contact_points: CrmContactPointsDep
):
    """Собирает ListCompaniesUseCase."""
    return ListCompaniesUseCase(repository, contact_points)


def get_update_company_use_case(
    repository: CompanyRepositoryDep,
    clock: ClockDep,
    contact_points: CrmContactPointsDep,
):
    """Собирает UpdateCompanyUseCase."""
    return UpdateCompanyUseCase(repository, clock, contact_points)


def get_delete_company_use_case(
    repository: CompanyRepositoryDep, contact_points: CrmContactPointsDep
):
    """Собирает DeleteCompanyUseCase."""
    return DeleteCompanyUseCase(repository, contact_points)


CreateCompanyUseCaseDep = Annotated[
    CreateCompanyUseCase, Depends(get_create_company_use_case)
]
GetCompanyUseCaseDep = Annotated[GetCompanyUseCase, Depends(get_get_company_use_case)]
ListCompaniesUseCaseDep = Annotated[
    ListCompaniesUseCase, Depends(get_list_companies_use_case)
]
UpdateCompanyUseCaseDep = Annotated[
    UpdateCompanyUseCase, Depends(get_update_company_use_case)
]
DeleteCompanyUseCaseDep = Annotated[
    DeleteCompanyUseCase, Depends(get_delete_company_use_case)
]


__all__ = [
    "CreateCompanyUseCaseDep",
    "CreateContactUseCaseDep",
    "DeleteCompanyUseCaseDep",
    "DeleteContactUseCaseDep",
    "GetCompanyUseCaseDep",
    "GetContactUseCaseDep",
    "ListCompaniesUseCaseDep",
    "ListContactsUseCaseDep",
    "UpdateCompanyUseCaseDep",
    "UpdateContactUseCaseDep",
]
