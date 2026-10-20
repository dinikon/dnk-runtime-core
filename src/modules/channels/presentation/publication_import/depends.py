from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.channels.presentation.depends.plugin_registry import (
    get_plugin_registry,
)
from src.modules.channels.presentation.publication_import.assembly import (
    build_publication_import_handlers,
)
from src.modules.channels.application.publication_import.command.start_publication_import.handler import (
    StartPublicationImportHandler,
)


def get_start_publication_import_handler(uow: UoWDep) -> StartPublicationImportHandler:
    """Собирает конкретный сценарий на общей сессии запроса."""
    return build_publication_import_handlers(uow.session, get_plugin_registry()).start


StartPublicationImportHandlerDep = Annotated[
    StartPublicationImportHandler, Depends(get_start_publication_import_handler)
]
from src.modules.channels.application.publication_import.command.retry_publication_import.handler import (
    RetryPublicationImportHandler,
)


def get_retry_publication_import_handler(uow: UoWDep) -> RetryPublicationImportHandler:
    """Собирает конкретный сценарий на общей сессии запроса."""
    return build_publication_import_handlers(uow.session, get_plugin_registry()).retry


RetryPublicationImportHandlerDep = Annotated[
    RetryPublicationImportHandler, Depends(get_retry_publication_import_handler)
]
from src.modules.channels.application.publication_import.command.cancel_publication_import.handler import (
    CancelPublicationImportHandler,
)


def get_cancel_publication_import_handler(
    uow: UoWDep,
) -> CancelPublicationImportHandler:
    """Собирает конкретный сценарий на общей сессии запроса."""
    return build_publication_import_handlers(uow.session, get_plugin_registry()).cancel


CancelPublicationImportHandlerDep = Annotated[
    CancelPublicationImportHandler, Depends(get_cancel_publication_import_handler)
]
from src.modules.channels.application.publication_import.query.get_publication_import.handler import (
    GetPublicationImportHandler,
)


def get_get_publication_import_handler(uow: UoWDep) -> GetPublicationImportHandler:
    """Собирает конкретный сценарий на общей сессии запроса."""
    return build_publication_import_handlers(uow.session, get_plugin_registry()).get


GetPublicationImportHandlerDep = Annotated[
    GetPublicationImportHandler, Depends(get_get_publication_import_handler)
]
from src.modules.channels.application.publication_import.query.get_publication_import_image.handler import (
    GetPublicationImportImageHandler,
)


def get_get_publication_import_image_handler(
    uow: UoWDep,
) -> GetPublicationImportImageHandler:
    """Собирает конкретный сценарий на общей сессии запроса."""
    return build_publication_import_handlers(uow.session, get_plugin_registry()).image


GetPublicationImportImageHandlerDep = Annotated[
    GetPublicationImportImageHandler, Depends(get_get_publication_import_image_handler)
]
