from typing import Annotated
from fastapi import Depends
from src.modules.channels.presentation.depends.handlers import ChannelsHandlersDep
from src.modules.channels.application.external_publication.query.get_external_publication.handler import (
    GetExternalPublicationHandler,
)
from src.modules.channels.application.external_publication.query.list_external_publications.handler import (
    ListExternalPublicationsHandler,
)


def get_get_external_publication_handler(
    handlers: ChannelsHandlersDep,
) -> GetExternalPublicationHandler:
    """Возвращает явно собранный обработчик get_external_publication."""
    return handlers.get_external_publication


GetExternalPublicationHandlerDep = Annotated[
    GetExternalPublicationHandler, Depends(get_get_external_publication_handler)
]


def get_list_external_publications_handler(
    handlers: ChannelsHandlersDep,
) -> ListExternalPublicationsHandler:
    """Возвращает явно собранный обработчик list_external_publications."""
    return handlers.list_external_publications


ListExternalPublicationsHandlerDep = Annotated[
    ListExternalPublicationsHandler, Depends(get_list_external_publications_handler)
]
