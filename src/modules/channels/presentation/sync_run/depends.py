from typing import Annotated
from fastapi import Depends
from src.modules.channels.presentation.depends.handlers import ChannelsHandlersDep
from src.modules.channels.application.sync_run.command.start_publication_initialization.handler import (
    StartPublicationInitializationHandler,
)
from src.modules.channels.application.sync_run.query.get_publication_initialization.handler import (
    GetPublicationInitializationHandler,
)


def get_start_publication_initialization_handler(
    handlers: ChannelsHandlersDep,
) -> StartPublicationInitializationHandler:
    """Возвращает явно собранный обработчик start_publication_initialization."""
    return handlers.start_publication_initialization


StartPublicationInitializationHandlerDep = Annotated[
    StartPublicationInitializationHandler,
    Depends(get_start_publication_initialization_handler),
]


def get_get_publication_initialization_handler(
    handlers: ChannelsHandlersDep,
) -> GetPublicationInitializationHandler:
    """Возвращает явно собранный обработчик get_publication_initialization."""
    return handlers.get_publication_initialization


GetPublicationInitializationHandlerDep = Annotated[
    GetPublicationInitializationHandler,
    Depends(get_get_publication_initialization_handler),
]
