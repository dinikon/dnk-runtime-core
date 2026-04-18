from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.crm.application.contact.use_case import (
    CreateContactUseCase,
    DeleteContactUseCase,
    DescribeContactFieldsUseCase,
    GetContactUseCase,
    ListContactsUseCase,
    UpdateContactUseCase,
)
from src.modules.crm.domain.contact.service import ContactService
from src.modules.crm.presentation.depends.infrastructure import (
    ContactCommandRepositoryDep,
    ContactFieldsDescriptionRepositoryDep,
    ContactQueryRepositoryDep,
)
from src.modules.shared.depends import ClockDep


def get_contact_service(
    command_repository: ContactCommandRepositoryDep,
    clock: ClockDep,
) -> ContactService:
    """Создает доменный сервис контактов для FastAPI DI."""

    return ContactService(
        command_repository=command_repository,
        clock=clock,
    )


ContactServiceDep = Annotated[ContactService, Depends(get_contact_service)]


def get_create_contact_use_case(
    service: ContactServiceDep,
) -> CreateContactUseCase:
    """Создает use case создания контакта."""
    return CreateContactUseCase(service)


CreateContactUseCaseDep = Annotated[
    CreateContactUseCase,
    Depends(get_create_contact_use_case),
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


def get_list_contacts_use_case(
    query_repository: ContactQueryRepositoryDep,
) -> ListContactsUseCase:
    """Создает use case списка контактов."""
    return ListContactsUseCase(query_repository)


ListContactsUseCaseDep = Annotated[
    ListContactsUseCase,
    Depends(get_list_contacts_use_case),
]


def get_update_contact_use_case(
    service: ContactServiceDep,
) -> UpdateContactUseCase:
    """Создает use case обновления контакта."""
    return UpdateContactUseCase(service)


UpdateContactUseCaseDep = Annotated[
    UpdateContactUseCase,
    Depends(get_update_contact_use_case),
]


def get_delete_contact_use_case(
    service: ContactServiceDep,
) -> DeleteContactUseCase:
    """Создает use case удаления контакта."""
    return DeleteContactUseCase(service)


DeleteContactUseCaseDep = Annotated[
    DeleteContactUseCase,
    Depends(get_delete_contact_use_case),
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


__all__ = [
    "ContactServiceDep",
    "CreateContactUseCaseDep",
    "DeleteContactUseCaseDep",
    "DescribeContactFieldsUseCaseDep",
    "GetContactUseCaseDep",
    "ListContactsUseCaseDep",
    "UpdateContactUseCaseDep",
    "get_contact_service",
    "get_create_contact_use_case",
    "get_delete_contact_use_case",
    "get_describe_contact_fields_use_case",
    "get_get_contact_use_case",
    "get_list_contacts_use_case",
    "get_update_contact_use_case",
]
