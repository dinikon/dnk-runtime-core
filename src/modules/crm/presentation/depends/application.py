from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.crm.application.company.use_case import (
    CreateCompanyUseCase,
    DeleteCompanyUseCase,
    DescribeCompanyFieldsUseCase,
    GetCompanyUseCase,
    ListCompaniesUseCase,
    UpdateCompanyUseCase,
)
from src.modules.crm.application.contact.use_case import (
    CreateContactUseCase,
    DeleteContactUseCase,
    DescribeContactFieldsUseCase,
    GetContactUseCase,
    ListContactsUseCase,
    UpdateContactUseCase,
)
from src.modules.crm.presentation.depends.infrastructure import (
    CompanyCommandRepositoryDep,
    CompanyFieldsDescriptionRepositoryDep,
    CompanyQueryRepositoryDep,
    ContactCommandRepositoryDep,
    ContactFieldsDescriptionRepositoryDep,
    ContactQueryRepositoryDep,
)
from src.modules.shared.depends import ClockDep


def get_create_contact_use_case(
    command_repository: ContactCommandRepositoryDep,
    clock: ClockDep,
) -> CreateContactUseCase:
    """Создает use case создания контакта."""
    return CreateContactUseCase(
        command_repository=command_repository,
        clock=clock,
    )


CreateContactUseCaseDep = Annotated[
    CreateContactUseCase,
    Depends(get_create_contact_use_case),
]


def get_create_company_use_case(
    command_repository: CompanyCommandRepositoryDep,
    clock: ClockDep,
) -> CreateCompanyUseCase:
    """Создает use case создания компании."""
    return CreateCompanyUseCase(
        command_repository=command_repository,
        clock=clock,
    )


CreateCompanyUseCaseDep = Annotated[
    CreateCompanyUseCase,
    Depends(get_create_company_use_case),
]


def get_get_contact_use_case(
    query_repository: ContactQueryRepositoryDep,
) -> GetContactUseCase:
    """Создает use case получения контакта."""
    return GetContactUseCase(query_repository)


GetContactUseCaseDep = Annotated[
    GetContactUseCase,
    Depends(get_get_contact_use_case),
]


def get_get_company_use_case(
    query_repository: CompanyQueryRepositoryDep,
) -> GetCompanyUseCase:
    """Создает use case получения компании."""
    return GetCompanyUseCase(query_repository)


GetCompanyUseCaseDep = Annotated[
    GetCompanyUseCase,
    Depends(get_get_company_use_case),
]


def get_list_contacts_use_case(
    query_repository: ContactQueryRepositoryDep,
) -> ListContactsUseCase:
    """Создает use case списка контактов."""
    return ListContactsUseCase(query_repository)


ListContactsUseCaseDep = Annotated[
    ListContactsUseCase,
    Depends(get_list_contacts_use_case),
]


def get_list_companies_use_case(
    query_repository: CompanyQueryRepositoryDep,
) -> ListCompaniesUseCase:
    """Создает use case списка компаний."""
    return ListCompaniesUseCase(query_repository)


ListCompaniesUseCaseDep = Annotated[
    ListCompaniesUseCase,
    Depends(get_list_companies_use_case),
]


def get_update_contact_use_case(
    command_repository: ContactCommandRepositoryDep,
    clock: ClockDep,
) -> UpdateContactUseCase:
    """Создает use case обновления контакта."""
    return UpdateContactUseCase(
        command_repository=command_repository,
        clock=clock,
    )


UpdateContactUseCaseDep = Annotated[
    UpdateContactUseCase,
    Depends(get_update_contact_use_case),
]


def get_update_company_use_case(
    command_repository: CompanyCommandRepositoryDep,
    clock: ClockDep,
) -> UpdateCompanyUseCase:
    """Создает use case обновления компании."""
    return UpdateCompanyUseCase(
        command_repository=command_repository,
        clock=clock,
    )


UpdateCompanyUseCaseDep = Annotated[
    UpdateCompanyUseCase,
    Depends(get_update_company_use_case),
]


def get_delete_contact_use_case(
    command_repository: ContactCommandRepositoryDep,
) -> DeleteContactUseCase:
    """Создает use case удаления контакта."""
    return DeleteContactUseCase(command_repository)


DeleteContactUseCaseDep = Annotated[
    DeleteContactUseCase,
    Depends(get_delete_contact_use_case),
]


def get_delete_company_use_case(
    command_repository: CompanyCommandRepositoryDep,
) -> DeleteCompanyUseCase:
    """Создает use case удаления компании."""
    return DeleteCompanyUseCase(command_repository)


DeleteCompanyUseCaseDep = Annotated[
    DeleteCompanyUseCase,
    Depends(get_delete_company_use_case),
]


def get_describe_contact_fields_use_case(
    repository: ContactFieldsDescriptionRepositoryDep,
) -> DescribeContactFieldsUseCase:
    """Создает use case чтения описания CRM-модели contact."""
    return DescribeContactFieldsUseCase(repository)


DescribeContactFieldsUseCaseDep = Annotated[
    DescribeContactFieldsUseCase,
    Depends(get_describe_contact_fields_use_case),
]


def get_describe_company_fields_use_case(
    repository: CompanyFieldsDescriptionRepositoryDep,
) -> DescribeCompanyFieldsUseCase:
    """Создает use case чтения описания CRM-модели company."""
    return DescribeCompanyFieldsUseCase(repository)


DescribeCompanyFieldsUseCaseDep = Annotated[
    DescribeCompanyFieldsUseCase,
    Depends(get_describe_company_fields_use_case),
]


__all__ = [
    "CreateCompanyUseCaseDep",
    "CreateContactUseCaseDep",
    "DeleteCompanyUseCaseDep",
    "DeleteContactUseCaseDep",
    "DescribeCompanyFieldsUseCaseDep",
    "DescribeContactFieldsUseCaseDep",
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
    "get_describe_company_fields_use_case",
    "get_describe_contact_fields_use_case",
    "get_get_company_use_case",
    "get_get_contact_use_case",
    "get_list_companies_use_case",
    "get_list_contacts_use_case",
    "get_update_company_use_case",
    "get_update_contact_use_case",
]
