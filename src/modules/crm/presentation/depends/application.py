from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.crm.application.use_cases import (
    CreateCompanyUseCase,
    CreateContactUseCase,
    DeleteCompanyUseCase,
    DeleteContactUseCase,
    GetCompanyUseCase,
    GetContactUseCase,
    ListCompaniesUseCase,
    ListContactsUseCase,
    UpdateCompanyUseCase,
    UpdateContactUseCase,
)
from src.modules.crm.presentation.depends.infrastructure import (
    CompanyRepositoryDep,
    ContactRepositoryDep,
    RuntimeRecordServiceDep,
)
from src.modules.shared.depends.uow import UoWDep


def get_create_contact_use_case(
    uow: UoWDep,
    contact_repository: ContactRepositoryDep,
    runtime_record_service: RuntimeRecordServiceDep,
) -> CreateContactUseCase:
    return CreateContactUseCase(
        uow=uow,
        contact_repository=contact_repository,
        runtime_record_service=runtime_record_service,
    )


CreateContactUseCaseDep = Annotated[
    CreateContactUseCase,
    Depends(get_create_contact_use_case),
]


def get_get_contact_use_case(
    contact_repository: ContactRepositoryDep,
    runtime_record_service: RuntimeRecordServiceDep,
) -> GetContactUseCase:
    return GetContactUseCase(
        contact_repository=contact_repository,
        runtime_record_service=runtime_record_service,
    )


GetContactUseCaseDep = Annotated[
    GetContactUseCase,
    Depends(get_get_contact_use_case),
]


def get_list_contacts_use_case(
    contact_repository: ContactRepositoryDep,
) -> ListContactsUseCase:
    return ListContactsUseCase(contact_repository=contact_repository)


ListContactsUseCaseDep = Annotated[
    ListContactsUseCase,
    Depends(get_list_contacts_use_case),
]


def get_update_contact_use_case(
    uow: UoWDep,
    contact_repository: ContactRepositoryDep,
    runtime_record_service: RuntimeRecordServiceDep,
) -> UpdateContactUseCase:
    return UpdateContactUseCase(
        uow=uow,
        contact_repository=contact_repository,
        runtime_record_service=runtime_record_service,
    )


UpdateContactUseCaseDep = Annotated[
    UpdateContactUseCase,
    Depends(get_update_contact_use_case),
]


def get_delete_contact_use_case(
    uow: UoWDep,
    contact_repository: ContactRepositoryDep,
) -> DeleteContactUseCase:
    return DeleteContactUseCase(uow=uow, contact_repository=contact_repository)


DeleteContactUseCaseDep = Annotated[
    DeleteContactUseCase,
    Depends(get_delete_contact_use_case),
]


def get_create_company_use_case(
    uow: UoWDep,
    company_repository: CompanyRepositoryDep,
    runtime_record_service: RuntimeRecordServiceDep,
) -> CreateCompanyUseCase:
    return CreateCompanyUseCase(
        uow=uow,
        company_repository=company_repository,
        runtime_record_service=runtime_record_service,
    )


CreateCompanyUseCaseDep = Annotated[
    CreateCompanyUseCase,
    Depends(get_create_company_use_case),
]


def get_get_company_use_case(
    company_repository: CompanyRepositoryDep,
    runtime_record_service: RuntimeRecordServiceDep,
) -> GetCompanyUseCase:
    return GetCompanyUseCase(
        company_repository=company_repository,
        runtime_record_service=runtime_record_service,
    )


GetCompanyUseCaseDep = Annotated[
    GetCompanyUseCase,
    Depends(get_get_company_use_case),
]


def get_list_companies_use_case(
    company_repository: CompanyRepositoryDep,
) -> ListCompaniesUseCase:
    return ListCompaniesUseCase(company_repository=company_repository)


ListCompaniesUseCaseDep = Annotated[
    ListCompaniesUseCase,
    Depends(get_list_companies_use_case),
]


def get_update_company_use_case(
    uow: UoWDep,
    company_repository: CompanyRepositoryDep,
    runtime_record_service: RuntimeRecordServiceDep,
) -> UpdateCompanyUseCase:
    return UpdateCompanyUseCase(
        uow=uow,
        company_repository=company_repository,
        runtime_record_service=runtime_record_service,
    )


UpdateCompanyUseCaseDep = Annotated[
    UpdateCompanyUseCase,
    Depends(get_update_company_use_case),
]


def get_delete_company_use_case(
    uow: UoWDep,
    company_repository: CompanyRepositoryDep,
) -> DeleteCompanyUseCase:
    return DeleteCompanyUseCase(uow=uow, company_repository=company_repository)


DeleteCompanyUseCaseDep = Annotated[
    DeleteCompanyUseCase,
    Depends(get_delete_company_use_case),
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
    "get_create_company_use_case",
    "get_create_contact_use_case",
    "get_delete_company_use_case",
    "get_delete_contact_use_case",
    "get_get_company_use_case",
    "get_get_contact_use_case",
    "get_list_companies_use_case",
    "get_list_contacts_use_case",
    "get_update_company_use_case",
    "get_update_contact_use_case",
]
