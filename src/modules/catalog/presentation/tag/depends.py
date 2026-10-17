from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.catalog.presentation.depends.common import (
    TagRepositoryDep,
    MutationLockDep,
    LocalesDep,
)
from src.modules.catalog.application.tag.port.query_repository import (
    TagQueryRepositoryProtocol,
)
from src.modules.catalog.infrastructure.tag.persistence.query_repository import (
    SqlAlchemyTagQueryRepository,
)
from src.modules.catalog.application.tag.command.create_tag.handler import (
    CreateTagHandler,
)
from src.modules.catalog.application.tag.command.put_tag_translation.handler import (
    PutTagTranslationHandler,
)
from src.modules.catalog.application.tag.command.delete_tag.handler import (
    DeleteTagHandler,
)
from src.modules.catalog.application.tag.query.get_tag.handler import (
    GetTagHandler,
)
from src.modules.catalog.application.tag.query.list_tags.handler import (
    ListTagsHandler,
)


def get_query_repository(uow: UoWDep) -> TagQueryRepositoryProtocol:
    """Собирает порт enum-проекций на общей tenant-сессии."""
    return SqlAlchemyTagQueryRepository(uow.session)


QueryRepositoryDep = Annotated[
    TagQueryRepositoryProtocol, Depends(get_query_repository)
]


def get_create_tag_handler(
    repository: TagRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    uuid: UuidDep,
    locales: LocalesDep,
) -> CreateTagHandler:
    """Собирает конкретный сценарий create_tag из именованных портов."""
    return CreateTagHandler(
        repository=repository, lock=lock, clock=clock, uuid=uuid, locales=locales
    )


CreateTagHandlerDep = Annotated[CreateTagHandler, Depends(get_create_tag_handler)]


def get_put_tag_translation_handler(
    repository: TagRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    locales: LocalesDep,
) -> PutTagTranslationHandler:
    """Собирает конкретный сценарий put_tag_translation из именованных портов."""
    return PutTagTranslationHandler(
        repository=repository, lock=lock, clock=clock, locales=locales
    )


PutTagTranslationHandlerDep = Annotated[
    PutTagTranslationHandler, Depends(get_put_tag_translation_handler)
]


def get_delete_tag_handler(
    repository: TagRepositoryDep, lock: MutationLockDep
) -> DeleteTagHandler:
    """Собирает конкретный сценарий delete_tag из именованных портов."""
    return DeleteTagHandler(repository=repository, lock=lock)


DeleteTagHandlerDep = Annotated[DeleteTagHandler, Depends(get_delete_tag_handler)]


def get_get_tag_handler(
    repository: QueryRepositoryDep, lock: MutationLockDep
) -> GetTagHandler:
    """Собирает конкретный сценарий get_tag из именованных портов."""
    return GetTagHandler(repository=repository, lock=lock)


GetTagHandlerDep = Annotated[GetTagHandler, Depends(get_get_tag_handler)]


def get_list_tags_handler(
    repository: QueryRepositoryDep, lock: MutationLockDep
) -> ListTagsHandler:
    """Собирает конкретный сценарий list_tags из именованных портов."""
    return ListTagsHandler(repository=repository, lock=lock)


ListTagsHandlerDep = Annotated[ListTagsHandler, Depends(get_list_tags_handler)]
