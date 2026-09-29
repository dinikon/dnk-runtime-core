from typing import Annotated

from fastapi import Depends

from src.config import dnk_config
from src.modules.crm.application.contact.command.create_contact.handler import (
    CreateContactHandler,
)
from src.modules.crm.domain.contact.repository import ContactRepositoryProtocol
from src.modules.crm.infrastructure.contact.persistence.repository import (
    SqlAlchemyContactRepository,
)
from src.modules.shared.application.persistence.tenant_schema_naming import (
    TenantSchemaNaming,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep


def get_contact_repository(uow: UoWDep) -> ContactRepositoryProtocol:
    """Собирает репозиторий на общей сессии текущего HTTP-запроса."""
    return SqlAlchemyContactRepository(
        uow.session, TenantSchemaNaming(dnk_config.SCHEMA_PREFIX)
    )


ContactRepositoryDep = Annotated[
    ContactRepositoryProtocol, Depends(get_contact_repository)
]


def get_create_contact_handler(
    repository: ContactRepositoryDep, clock: ClockDep
) -> CreateContactHandler:
    """Подключает порты к обработчику создания контакта."""
    return CreateContactHandler(repository, clock)


CreateContactHandlerDep = Annotated[
    CreateContactHandler, Depends(get_create_contact_handler)
]
