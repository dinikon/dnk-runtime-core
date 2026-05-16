from src.modules.crm.presentation.depends.application import (
    CreateContactUseCaseDep,
    DeleteContactUseCaseDep,
    GetContactUseCaseDep,
    ListContactsUseCaseDep,
    UpdateContactUseCaseDep,
    get_create_contact_use_case,
    get_delete_contact_use_case,
    get_get_contact_use_case,
    get_list_contacts_use_case,
    get_update_contact_use_case,
)
from src.modules.crm.presentation.depends.infrastructure import (
    ContactCommandRepositoryDep,
    ContactQueryRepositoryDep,
    get_contact_command_repository,
    get_contact_query_repository,
)

__all__ = [
    "ContactCommandRepositoryDep",
    "ContactQueryRepositoryDep",
    "CreateContactUseCaseDep",
    "DeleteContactUseCaseDep",
    "GetContactUseCaseDep",
    "ListContactsUseCaseDep",
    "UpdateContactUseCaseDep",
    "get_contact_command_repository",
    "get_contact_query_repository",
    "get_create_contact_use_case",
    "get_delete_contact_use_case",
    "get_get_contact_use_case",
    "get_list_contacts_use_case",
    "get_update_contact_use_case",
]
