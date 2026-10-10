from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.catalog.presentation.depends.common import (
    AttributeRepositoryDep,
    MutationLockDep,
    LocalesDep,
)
from src.modules.catalog.application.attribute.port.query_repository import (
    AttributeQueryRepositoryProtocol,
)
from src.modules.catalog.infrastructure.attribute.persistence.query_repository import (
    SqlAlchemyAttributeQueryRepository,
)
from src.modules.catalog.application.attribute.command.create_attribute.handler import (
    CreateAttributeHandler,
)
from src.modules.catalog.application.attribute.command.put_attribute_translation.handler import (
    PutAttributeTranslationHandler,
)
from src.modules.catalog.application.attribute.command.replace_attribute_options.handler import (
    ReplaceAttributeOptionsHandler,
)
from src.modules.catalog.application.attribute.command.delete_attribute.handler import (
    DeleteAttributeHandler,
)
from src.modules.catalog.application.attribute.query.get_attribute.handler import (
    GetAttributeHandler,
)
from src.modules.catalog.application.attribute.query.list_attributes.handler import (
    ListAttributesHandler,
)


def get_query_repository(uow: UoWDep) -> AttributeQueryRepositoryProtocol:
    """Собирает порт enum-проекций на общей tenant-сессии."""
    return SqlAlchemyAttributeQueryRepository(uow.session)


QueryRepositoryDep = Annotated[
    AttributeQueryRepositoryProtocol, Depends(get_query_repository)
]


def get_create_attribute_handler(
    repository: AttributeRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    uuid: UuidDep,
    locales: LocalesDep,
) -> CreateAttributeHandler:
    """Собирает конкретный сценарий create_attribute из именованных портов."""
    return CreateAttributeHandler(
        repository=repository, lock=lock, clock=clock, uuid=uuid, locales=locales
    )


CreateAttributeHandlerDep = Annotated[
    CreateAttributeHandler, Depends(get_create_attribute_handler)
]


def get_put_attribute_translation_handler(
    repository: AttributeRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    locales: LocalesDep,
) -> PutAttributeTranslationHandler:
    """Собирает конкретный сценарий put_attribute_translation из именованных портов."""
    return PutAttributeTranslationHandler(
        repository=repository, lock=lock, clock=clock, locales=locales
    )


PutAttributeTranslationHandlerDep = Annotated[
    PutAttributeTranslationHandler, Depends(get_put_attribute_translation_handler)
]


def get_replace_attribute_options_handler(
    repository: AttributeRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    uuid: UuidDep,
    locales: LocalesDep,
) -> ReplaceAttributeOptionsHandler:
    """Собирает конкретный сценарий replace_attribute_options из именованных портов."""
    return ReplaceAttributeOptionsHandler(
        repository=repository, lock=lock, clock=clock, uuid=uuid, locales=locales
    )


ReplaceAttributeOptionsHandlerDep = Annotated[
    ReplaceAttributeOptionsHandler, Depends(get_replace_attribute_options_handler)
]


def get_delete_attribute_handler(
    repository: AttributeRepositoryDep, lock: MutationLockDep
) -> DeleteAttributeHandler:
    """Собирает конкретный сценарий delete_attribute из именованных портов."""
    return DeleteAttributeHandler(repository=repository, lock=lock)


DeleteAttributeHandlerDep = Annotated[
    DeleteAttributeHandler, Depends(get_delete_attribute_handler)
]


def get_get_attribute_handler(
    repository: QueryRepositoryDep, lock: MutationLockDep
) -> GetAttributeHandler:
    """Собирает конкретный сценарий get_attribute из именованных портов."""
    return GetAttributeHandler(repository=repository, lock=lock)


GetAttributeHandlerDep = Annotated[
    GetAttributeHandler, Depends(get_get_attribute_handler)
]


def get_list_attributes_handler(
    repository: QueryRepositoryDep, lock: MutationLockDep
) -> ListAttributesHandler:
    """Собирает конкретный сценарий list_attributes из именованных портов."""
    return ListAttributesHandler(repository=repository, lock=lock)


ListAttributesHandlerDep = Annotated[
    ListAttributesHandler, Depends(get_list_attributes_handler)
]
