from typing import Annotated
from fastapi import Depends
from src.modules.channels.application.external_publication.query.list_publications.handler import (
    ListPublicationsHandler,
)
from src.modules.channels.application.external_publication.query.get_publication.handler import (
    GetPublicationHandler,
)
from src.modules.channels.infrastructure.external_publication.persistence.query_repository import (
    SqlAlchemyPublicationQueryRepository,
)
from src.modules.channels.infrastructure.channel.persistence.query_repository import (
    SqlAlchemyChannelQueryRepository,
)
from src.modules.channels.infrastructure.channel.definitions.registry import (
    CodeChannelRegistry,
)
from src.modules.shared.presentation.persistence.depends import UoWDep


def get_list_publications_handler(uow: UoWDep) -> ListPublicationsHandler:
    """Собирает сценарий списка на безопасных tenant-проекциях."""
    return ListPublicationsHandler(
        SqlAlchemyPublicationQueryRepository(uow.session),
        SqlAlchemyChannelQueryRepository(uow.session, CodeChannelRegistry()),
    )


ListPublicationsHandlerDep = Annotated[
    ListPublicationsHandler, Depends(get_list_publications_handler)
]


def get_get_publication_handler(uow: UoWDep) -> GetPublicationHandler:
    """Собирает сценарий чтения отрендеренной карточки публикации."""
    return GetPublicationHandler(
        SqlAlchemyPublicationQueryRepository(uow.session),
        SqlAlchemyChannelQueryRepository(uow.session, CodeChannelRegistry()),
    )


GetPublicationHandlerDep = Annotated[
    GetPublicationHandler, Depends(get_get_publication_handler)
]
