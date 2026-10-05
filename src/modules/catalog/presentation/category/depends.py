from typing import Annotated

from fastapi import Depends

from src.modules.catalog.application.category.command.create_category.handler import (
    CreateCategoryHandler,
)
from src.modules.catalog.application.category.command.delete_category.handler import (
    DeleteCategoryHandler,
)
from src.modules.catalog.application.category.command.move_category.handler import (
    MoveCategoryHandler,
)
from src.modules.catalog.application.category.command.put_category_content.handler import (
    PutCategoryContentHandler,
)
from src.modules.catalog.application.category.port.query_repository import (
    CategoryQueryRepositoryProtocol,
)
from src.modules.catalog.application.category.query.get_category.handler import (
    GetCategoryHandler,
)
from src.modules.catalog.application.category.query.list_categories.handler import (
    ListCategoriesHandler,
)
from src.modules.catalog.application.category.port.locale_reader import (
    CategoryLocaleReaderPort,
)
from src.modules.catalog.domain.category.repository import CategoryRepositoryProtocol
from src.modules.catalog.infrastructure.category.persistence.query_repository import (
    SqlAlchemyCategoryQueryRepository,
)
from src.modules.catalog.infrastructure.category.persistence.repository import (
    SqlAlchemyCategoryRepository,
)
from src.modules.catalog.infrastructure.reference_locale_reader import (
    ReferenceLocaleReaderAdapter,
)
from src.modules.reference_data.infrastructure.persistence.repository import (
    SqlAlchemyCatalogRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_category_repository(uow: UoWDep) -> CategoryRepositoryProtocol:
    return SqlAlchemyCategoryRepository(uow.session)


CategoryRepositoryDep = Annotated[
    CategoryRepositoryProtocol, Depends(get_category_repository)
]


def get_category_query_repository(uow: UoWDep) -> CategoryQueryRepositoryProtocol:
    return SqlAlchemyCategoryQueryRepository(uow.session)


CategoryQueryRepositoryDep = Annotated[
    CategoryQueryRepositoryProtocol, Depends(get_category_query_repository)
]


def get_category_locale_reader(uow: UoWDep) -> CategoryLocaleReaderPort:
    return ReferenceLocaleReaderAdapter(SqlAlchemyCatalogRepository(uow.session))


CategoryLocaleReaderDep = Annotated[
    CategoryLocaleReaderPort, Depends(get_category_locale_reader)
]


def get_create_category_handler(
    repository: CategoryRepositoryDep,
    locales: CategoryLocaleReaderDep,
    clock: ClockDep,
    uuids: UuidDep,
) -> CreateCategoryHandler:
    return CreateCategoryHandler(repository, locales, clock, uuids)


CreateCategoryHandlerDep = Annotated[
    CreateCategoryHandler, Depends(get_create_category_handler)
]


def get_put_category_content_handler(
    repository: CategoryRepositoryDep, locales: CategoryLocaleReaderDep, clock: ClockDep
) -> PutCategoryContentHandler:
    return PutCategoryContentHandler(repository, locales, clock)


PutCategoryContentHandlerDep = Annotated[
    PutCategoryContentHandler, Depends(get_put_category_content_handler)
]


def get_move_category_handler(
    repository: CategoryRepositoryDep, clock: ClockDep
) -> MoveCategoryHandler:
    return MoveCategoryHandler(repository, clock)


MoveCategoryHandlerDep = Annotated[
    MoveCategoryHandler, Depends(get_move_category_handler)
]


def get_delete_category_handler(
    repository: CategoryRepositoryDep,
) -> DeleteCategoryHandler:
    return DeleteCategoryHandler(repository)


DeleteCategoryHandlerDep = Annotated[
    DeleteCategoryHandler, Depends(get_delete_category_handler)
]


def get_get_category_handler(
    repository: CategoryQueryRepositoryDep,
) -> GetCategoryHandler:
    return GetCategoryHandler(repository)


GetCategoryHandlerDep = Annotated[GetCategoryHandler, Depends(get_get_category_handler)]


def get_list_categories_handler(
    repository: CategoryQueryRepositoryDep,
) -> ListCategoriesHandler:
    return ListCategoriesHandler(repository)


ListCategoriesHandlerDep = Annotated[
    ListCategoriesHandler, Depends(get_list_categories_handler)
]
