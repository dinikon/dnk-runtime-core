from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from src.modules.crm.application.contact.use_case import (
    CreateContactUseCase,
    DeleteContactUseCase,
    GetContactUseCase,
    ListContactsUseCase,
    UpdateContactUseCase,
)
from src.modules.crm.domain.contact.service import ContactService
from src.modules.crm.presentation.depends.infrastructure import (
    ContactCommandRepositoryDep,
    ContactQueryRepositoryDep,
)
from src.modules.shared.depends import ClockDep


def get_contact_service(
    command_repository: ContactCommandRepositoryDep,
    clock: ClockDep,
) -> ContactService:
    return ContactService(
        command_repository=command_repository,
        clock=clock,
    )


ContactServiceDep = Annotated[ContactService, Depends(get_contact_service)]


def get_create_contact_use_case(
    service: ContactServiceDep,
) -> CreateContactUseCase:
    return CreateContactUseCase(service)


CreateContactUseCaseDep = Annotated[
    CreateContactUseCase,
    Depends(get_create_contact_use_case),
]


def get_get_contact_use_case(
    service: ContactServiceDep,
) -> GetContactUseCase:
    return GetContactUseCase(service)


GetContactUseCaseDep = Annotated[
    GetContactUseCase,
    Depends(get_get_contact_use_case),
]


def get_list_contacts_use_case(
    query_repository: ContactQueryRepositoryDep,
) -> ListContactsUseCase:
    return ListContactsUseCase(query_repository)


ListContactsUseCaseDep = Annotated[
    ListContactsUseCase,
    Depends(get_list_contacts_use_case),
]


def get_update_contact_use_case(
    service: ContactServiceDep,
) -> UpdateContactUseCase:
    return UpdateContactUseCase(service)


UpdateContactUseCaseDep = Annotated[
    UpdateContactUseCase,
    Depends(get_update_contact_use_case),
]


def get_delete_contact_use_case(
    service: ContactServiceDep,
) -> DeleteContactUseCase:
    return DeleteContactUseCase(service)


DeleteContactUseCaseDep = Annotated[
    DeleteContactUseCase,
    Depends(get_delete_contact_use_case),
]


__all__ = [
    "ContactServiceDep",
    "CreateContactUseCaseDep",
    "DeleteContactUseCaseDep",
    "GetContactUseCaseDep",
    "ListContactsUseCaseDep",
    "UpdateContactUseCaseDep",
    "get_contact_service",
    "get_create_contact_use_case",
    "get_delete_contact_use_case",
    "get_get_contact_use_case",
    "get_list_contacts_use_case",
    "get_update_contact_use_case",
]
