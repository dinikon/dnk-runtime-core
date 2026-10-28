"""Сборка read-side публикаций без подключения worker."""

from typing import Annotated

from fastapi import Depends

from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.channels.presentation.depends import get_platforms
from src.modules.channels.application.external_publication.query.list_publications.handler import (
    ListPublicationsHandler,
)
from src.modules.channels.application.external_publication.query.get_publication.handler import (
    GetPublicationHandler,
)
from src.modules.channels.infrastructure.external_publication.persistence.query_repository import (
    SqlAlchemyPublicationQueryRepository,
)


def get_list_publications_handler(uow: UoWDep) -> ListPublicationsHandler:
    """Собирает список карточек на общей tenant-сессии."""
    return ListPublicationsHandler(
        SqlAlchemyPublicationQueryRepository(uow.session), get_platforms()
    )


ListPublicationsHandlerDep = Annotated[
    ListPublicationsHandler, Depends(get_list_publications_handler)
]


def get_get_publication_handler(uow: UoWDep) -> GetPublicationHandler:
    """Собирает чтение карточки и выбранной разновидности."""
    return GetPublicationHandler(
        SqlAlchemyPublicationQueryRepository(uow.session), get_platforms()
    )


GetPublicationHandlerDep = Annotated[
    GetPublicationHandler, Depends(get_get_publication_handler)
]
