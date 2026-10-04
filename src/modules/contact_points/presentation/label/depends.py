from typing import Annotated

from fastapi import Depends

from src.modules.contact_points.application.label.command.create_label.handler import (
    CreateContactPointLabelHandler,
)
from src.modules.contact_points.application.label.command.update_label.handler import (
    UpdateContactPointLabelHandler,
)
from src.modules.contact_points.application.label.query.list_labels.handler import (
    ListContactPointLabelsHandler,
)
from src.modules.contact_points.infrastructure.label.persistence.repository import (
    SqlAlchemyContactPointLabelRepository,
)
from src.modules.contact_points.presentation.depends.naming import TenantNamingDep
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep


def get_label_repository(
    uow: UoWDep, naming: TenantNamingDep
) -> SqlAlchemyContactPointLabelRepository:
    """Собирает repository подписей на общей сессии."""
    return SqlAlchemyContactPointLabelRepository(uow.session, naming)


ContactPointLabelRepositoryDep = Annotated[
    SqlAlchemyContactPointLabelRepository, Depends(get_label_repository)
]


def get_create_label_handler(
    repository: ContactPointLabelRepositoryDep, clock: ClockDep
) -> CreateContactPointLabelHandler:
    """Собирает создание подписи."""
    return CreateContactPointLabelHandler(repository, clock)


CreateContactPointLabelHandlerDep = Annotated[
    CreateContactPointLabelHandler, Depends(get_create_label_handler)
]


def get_update_label_handler(
    repository: ContactPointLabelRepositoryDep, clock: ClockDep
) -> UpdateContactPointLabelHandler:
    """Собирает изменение подписи."""
    return UpdateContactPointLabelHandler(repository, clock)


UpdateContactPointLabelHandlerDep = Annotated[
    UpdateContactPointLabelHandler, Depends(get_update_label_handler)
]


def get_list_labels_handler(
    repository: ContactPointLabelRepositoryDep,
) -> ListContactPointLabelsHandler:
    """Собирает чтение подписей."""
    return ListContactPointLabelsHandler(repository)


ListContactPointLabelsHandlerDep = Annotated[
    ListContactPointLabelsHandler, Depends(get_list_labels_handler)
]
