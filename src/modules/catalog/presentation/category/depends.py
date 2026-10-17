from src.modules.catalog.presentation.depends.common import CategoryTreeDep
from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.catalog.presentation.depends.common import (
    CategoryRepositoryDep,
    MutationLockDep,
    LocalesDep,
)
from src.modules.catalog.application.category.port.query_repository import (
    CategoryQueryRepositoryProtocol,
)
from src.modules.catalog.infrastructure.category.persistence.query_repository import (
    SqlAlchemyCategoryQueryRepository,
)
from src.modules.catalog.application.category.command.create_category.handler import (
    CreateCategoryHandler,
)
from src.modules.catalog.application.category.command.put_category_content.handler import (
    PutCategoryContentHandler,
)
from src.modules.catalog.application.category.command.delete_category.handler import (
    DeleteCategoryHandler,
)
from src.modules.catalog.application.category.query.get_category.handler import (
    GetCategoryHandler,
)
from src.modules.catalog.application.category.query.list_categories.handler import (
    ListCategoriesHandler,
)


def get_query_repository(uow: UoWDep) -> CategoryQueryRepositoryProtocol:
    """Собирает порт enum-проекций на общей tenant-сессии."""
    return SqlAlchemyCategoryQueryRepository(uow.session)


QueryRepositoryDep = Annotated[
    CategoryQueryRepositoryProtocol, Depends(get_query_repository)
]


def get_create_category_handler(
    repository: CategoryRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    uuid: UuidDep,
    locales: LocalesDep,
    tree: CategoryTreeDep,
) -> CreateCategoryHandler:
    """Собирает конкретный сценарий create_category из именованных портов."""
    return CreateCategoryHandler(
        repository=repository,
        lock=lock,
        clock=clock,
        uuid=uuid,
        locales=locales,
        tree=tree,
    )


CreateCategoryHandlerDep = Annotated[
    CreateCategoryHandler, Depends(get_create_category_handler)
]


def get_put_category_content_handler(
    repository: CategoryRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    locales: LocalesDep,
) -> PutCategoryContentHandler:
    """Собирает конкретный сценарий put_category_content из именованных портов."""
    return PutCategoryContentHandler(
        repository=repository, lock=lock, clock=clock, locales=locales
    )


PutCategoryContentHandlerDep = Annotated[
    PutCategoryContentHandler, Depends(get_put_category_content_handler)
]


def get_delete_category_handler(
    repository: CategoryRepositoryDep, lock: MutationLockDep
) -> DeleteCategoryHandler:
    """Собирает конкретный сценарий delete_category из именованных портов."""
    return DeleteCategoryHandler(repository=repository, lock=lock)


DeleteCategoryHandlerDep = Annotated[
    DeleteCategoryHandler, Depends(get_delete_category_handler)
]


def get_get_category_handler(
    repository: QueryRepositoryDep, lock: MutationLockDep
) -> GetCategoryHandler:
    """Собирает конкретный сценарий get_category из именованных портов."""
    return GetCategoryHandler(repository=repository, lock=lock)


GetCategoryHandlerDep = Annotated[GetCategoryHandler, Depends(get_get_category_handler)]


def get_list_categories_handler(
    repository: QueryRepositoryDep, lock: MutationLockDep
) -> ListCategoriesHandler:
    """Собирает конкретный сценарий list_categories из именованных портов."""
    return ListCategoriesHandler(repository=repository, lock=lock)


ListCategoriesHandlerDep = Annotated[
    ListCategoriesHandler, Depends(get_list_categories_handler)
]

from src.modules.catalog.application.category.command.move_category.handler import (
    MoveCategoryHandler,
)


def get_move_category_handler(
    repository: CategoryRepositoryDep,
    tree: CategoryTreeDep,
    lock: MutationLockDep,
    clock: ClockDep,
) -> MoveCategoryHandler:
    """Собирает сценарий перемещения на портах одного UoW."""
    return MoveCategoryHandler(repository=repository, tree=tree, lock=lock, clock=clock)


MoveCategoryHandlerDep = Annotated[
    MoveCategoryHandler, Depends(get_move_category_handler)
]
