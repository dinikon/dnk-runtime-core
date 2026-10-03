from typing import Annotated

from fastapi import Depends

from src.modules.crm.application.contact.command.create_contact.handler import (
    CreateContactHandler,
)
from src.modules.crm.application.contact.command.delete_contact.handler import (
    DeleteContactHandler,
)
from src.modules.crm.application.contact.command.update_contact.handler import (
    UpdateContactHandler,
)
from src.modules.crm.application.contact.query.list_contacts.handler import (
    ListContactsHandler,
)
from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol
from src.modules.crm.application.contact.port.query_repository import (
    ContactQueryRepositoryProtocol,
)
from src.modules.crm.application.contact.query.get_contact.handler import (
    GetContactHandler,
)
from src.modules.crm.infrastructure.contact.persistence.query_repository import (
    SqlAlchemyContactQueryRepository,
)
from src.modules.crm.infrastructure.contact.persistence.repository import (
    SqlAlchemyContactRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_contact_repository(uow: UoWDep) -> ContactRepositoryProtocol:
    """Собирает репозиторий на общей сессии текущего HTTP-запроса."""
    return SqlAlchemyContactRepository(uow.session)


ContactRepositoryDep = Annotated[
    ContactRepositoryProtocol, Depends(get_contact_repository)
]


def get_create_contact_handler(
    repository: ContactRepositoryDep, clock: ClockDep, uuid_generator: UuidDep
) -> CreateContactHandler:
    """Подключает порты к обработчику создания контакта."""
    return CreateContactHandler(repository, clock, uuid_generator)


CreateContactHandlerDep = Annotated[
    CreateContactHandler, Depends(get_create_contact_handler)
]


def get_contact_query_repository(uow: UoWDep) -> ContactQueryRepositoryProtocol:
    """Подключает чтение контактов к общей сессии HTTP-запроса."""
    return SqlAlchemyContactQueryRepository(uow.session)


ContactQueryRepositoryDep = Annotated[
    ContactQueryRepositoryProtocol, Depends(get_contact_query_repository)
]


def get_get_contact_handler(repository: ContactQueryRepositoryDep) -> GetContactHandler:
    """Собирает обработчик чтения без clock и генератора идентификаторов."""
    return GetContactHandler(repository)


GetContactHandlerDep = Annotated[GetContactHandler, Depends(get_get_contact_handler)]


def get_list_contacts_handler(
    repository: ContactQueryRepositoryDep,
) -> ListContactsHandler:
    return ListContactsHandler(repository)


ListContactsHandlerDep = Annotated[
    ListContactsHandler, Depends(get_list_contacts_handler)
]


def get_update_contact_handler(
    repository: ContactRepositoryDep, clock: ClockDep
) -> UpdateContactHandler:
    return UpdateContactHandler(repository, clock)


UpdateContactHandlerDep = Annotated[
    UpdateContactHandler, Depends(get_update_contact_handler)
]


def get_delete_contact_handler(
    repository: ContactRepositoryDep,
) -> DeleteContactHandler:
    return DeleteContactHandler(repository)


DeleteContactHandlerDep = Annotated[
    DeleteContactHandler, Depends(get_delete_contact_handler)
]
