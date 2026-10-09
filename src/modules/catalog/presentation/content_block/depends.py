from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.catalog.presentation.depends.common import (
    ContentBlockRepositoryDep,
    MutationLockDep,
    LocalesDep,
)
from src.modules.catalog.application.content_block.port.query_repository import (
    ContentBlockQueryRepositoryProtocol,
)
from src.modules.catalog.infrastructure.content_block.persistence.query_repository import (
    SqlAlchemyContentBlockQueryRepository,
)
from src.modules.catalog.application.content_block.command.create_content_block.handler import (
    CreateContentBlockHandler,
)
from src.modules.catalog.application.content_block.command.delete_content_block.handler import (
    DeleteContentBlockHandler,
)
from src.modules.catalog.application.content_block.command.update_content_block.handler import (
    UpdateContentBlockHandler,
)
from src.modules.catalog.application.content_block.query.get_content_block.handler import (
    GetContentBlockHandler,
)
from src.modules.catalog.application.content_block.query.list_content_blocks.handler import (
    ListContentBlocksHandler,
)


def get_query_repository(uow: UoWDep) -> ContentBlockQueryRepositoryProtocol:
    """Собирает read repository текущего корня на tenant-сессии."""
    return SqlAlchemyContentBlockQueryRepository(uow.session)


QueryRepositoryDep = Annotated[
    ContentBlockQueryRepositoryProtocol, Depends(get_query_repository)
]


def get_create_content_block_handler(
    repository: ContentBlockRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    uuid: UuidDep,
    locales: LocalesDep,
) -> CreateContentBlockHandler:
    """Собирает конкретный сценарий create_content_block из необходимых портов."""
    return CreateContentBlockHandler(
        repository=repository, lock=lock, clock=clock, uuid=uuid, locales=locales
    )


CreateContentBlockHandlerDep = Annotated[
    CreateContentBlockHandler, Depends(get_create_content_block_handler)
]


def get_delete_content_block_handler(
    repository: ContentBlockRepositoryDep, lock: MutationLockDep
) -> DeleteContentBlockHandler:
    """Собирает конкретный сценарий delete_content_block из необходимых портов."""
    return DeleteContentBlockHandler(repository=repository, lock=lock)


DeleteContentBlockHandlerDep = Annotated[
    DeleteContentBlockHandler, Depends(get_delete_content_block_handler)
]


def get_update_content_block_handler(
    repository: ContentBlockRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    locales: LocalesDep,
) -> UpdateContentBlockHandler:
    """Собирает конкретный сценарий update_content_block из необходимых портов."""
    return UpdateContentBlockHandler(
        repository=repository, lock=lock, clock=clock, locales=locales
    )


UpdateContentBlockHandlerDep = Annotated[
    UpdateContentBlockHandler, Depends(get_update_content_block_handler)
]


def get_get_content_block_handler(
    lock: MutationLockDep,
    repository: QueryRepositoryDep,
) -> GetContentBlockHandler:
    """Собирает конкретный сценарий get_content_block из необходимых портов."""
    return GetContentBlockHandler(repository=repository, lock=lock)


GetContentBlockHandlerDep = Annotated[
    GetContentBlockHandler, Depends(get_get_content_block_handler)
]


def get_list_content_blocks_handler(
    lock: MutationLockDep,
    repository: QueryRepositoryDep,
) -> ListContentBlocksHandler:
    """Собирает конкретный сценарий list_content_blocks из необходимых портов."""
    return ListContentBlocksHandler(repository=repository, lock=lock)


ListContentBlocksHandlerDep = Annotated[
    ListContentBlocksHandler, Depends(get_list_content_blocks_handler)
]
