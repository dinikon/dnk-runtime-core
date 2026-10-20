from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.channels.presentation.depends.plugin_registry import (
    get_plugin_registry,
)
from src.modules.channels.presentation.content_update.assembly import (
    build_content_update_handlers,
)

from src.modules.channels.application.content_update.command.start_content_update.handler import (
    StartContentUpdateHandler,
)


def get_start_content_update_handler(uow: UoWDep) -> StartContentUpdateHandler:
    """Собирает конкретный сценарий в общей транзакции запроса."""
    return build_content_update_handlers(uow.session, get_plugin_registry()).start


StartContentUpdateHandlerDep = Annotated[
    StartContentUpdateHandler, Depends(get_start_content_update_handler)
]

from src.modules.channels.application.content_update.command.confirm_content_update.handler import (
    ConfirmContentUpdateHandler,
)


def get_confirm_content_update_handler(uow: UoWDep) -> ConfirmContentUpdateHandler:
    """Собирает конкретный сценарий в общей транзакции запроса."""
    return build_content_update_handlers(uow.session, get_plugin_registry()).confirm


ConfirmContentUpdateHandlerDep = Annotated[
    ConfirmContentUpdateHandler, Depends(get_confirm_content_update_handler)
]

from src.modules.channels.application.content_update.command.retry_content_update.handler import (
    RetryContentUpdateHandler,
)


def get_retry_content_update_handler(uow: UoWDep) -> RetryContentUpdateHandler:
    """Собирает конкретный сценарий в общей транзакции запроса."""
    return build_content_update_handlers(uow.session, get_plugin_registry()).retry


RetryContentUpdateHandlerDep = Annotated[
    RetryContentUpdateHandler, Depends(get_retry_content_update_handler)
]

from src.modules.channels.application.content_update.query.get_content_update.handler import (
    GetContentUpdateHandler,
)


def get_get_content_update_handler(uow: UoWDep) -> GetContentUpdateHandler:
    """Собирает конкретный сценарий в общей транзакции запроса."""
    return build_content_update_handlers(uow.session, get_plugin_registry()).get


GetContentUpdateHandlerDep = Annotated[
    GetContentUpdateHandler, Depends(get_get_content_update_handler)
]

from src.modules.channels.application.content_update.query.list_content_updates.handler import (
    ListContentUpdatesHandler,
)


def get_list_content_updates_handler(uow: UoWDep) -> ListContentUpdatesHandler:
    """Собирает конкретный сценарий в общей транзакции запроса."""
    return build_content_update_handlers(uow.session, get_plugin_registry()).listing


ListContentUpdatesHandlerDep = Annotated[
    ListContentUpdatesHandler, Depends(get_list_content_updates_handler)
]
