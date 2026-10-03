from typing import Annotated

from fastapi import Depends

from src.modules.crm.application.contact.command.create_contact.handler import (
    CreateContactHandler,
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
