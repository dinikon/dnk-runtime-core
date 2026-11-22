from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.catalog.presentation.depends.common import LocalesDep
from src.modules.catalog.infrastructure.catalog_category.repository import (
    SqlAlchemyCatalogCategoryRepository,
)
from src.modules.catalog.infrastructure.catalog_category.query_repository import (
    SqlAlchemyCatalogCategoryQueryRepository,
)
from src.modules.catalog.domain.catalog_category.repository import (
    CatalogCategoryRepositoryProtocol,
)
from src.modules.catalog.application.catalog_category.command.create_catalog_category.handler import (
    CreateCatalogCategoryHandler,
)
from src.modules.catalog.application.catalog_category.command.update_catalog_category.handler import (
    UpdateCatalogCategoryHandler,
)
from src.modules.catalog.application.catalog_category.command.delete_catalog_category.handler import (
    DeleteCatalogCategoryHandler,
)
from src.modules.catalog.application.catalog_category.command.set_default_catalog_category.handler import (
    SetDefaultCatalogCategoryHandler,
)
from src.modules.catalog.application.catalog_category.query.list_catalog_categories.handler import (
    ListCatalogCategoriesHandler,
)


def get_catalog_category_repository(uow: UoWDep) -> CatalogCategoryRepositoryProtocol:
    """Собирает зависимости сценария в общем tenant UoW."""
    return SqlAlchemyCatalogCategoryRepository(uow.session)


CategoryRepositoryDep = Annotated[
    CatalogCategoryRepositoryProtocol, Depends(get_catalog_category_repository)
]


def get_create_catalog_category_handler(
    repository: CategoryRepositoryDep, locales: LocalesDep, uuid: UuidDep
) -> CreateCatalogCategoryHandler:
    """Собирает зависимости сценария в общем tenant UoW."""
    return CreateCatalogCategoryHandler(repository, locales, uuid)


CreateCatalogCategoryHandlerDep = Annotated[
    CreateCatalogCategoryHandler, Depends(get_create_catalog_category_handler)
]


def get_update_catalog_category_handler(
    repository: CategoryRepositoryDep, locales: LocalesDep
) -> UpdateCatalogCategoryHandler:
    """Собирает зависимости сценария в общем tenant UoW."""
    return UpdateCatalogCategoryHandler(repository, locales)


UpdateCatalogCategoryHandlerDep = Annotated[
    UpdateCatalogCategoryHandler, Depends(get_update_catalog_category_handler)
]


def get_delete_catalog_category_handler(
    repository: CategoryRepositoryDep,
) -> DeleteCatalogCategoryHandler:
    """Собирает зависимости сценария в общем tenant UoW."""
    return DeleteCatalogCategoryHandler(repository)


DeleteCatalogCategoryHandlerDep = Annotated[
    DeleteCatalogCategoryHandler, Depends(get_delete_catalog_category_handler)
]


def get_set_default_catalog_category_handler(
    repository: CategoryRepositoryDep,
) -> SetDefaultCatalogCategoryHandler:
    """Собирает зависимости сценария в общем tenant UoW."""
    return SetDefaultCatalogCategoryHandler(repository)


SetDefaultCatalogCategoryHandlerDep = Annotated[
    SetDefaultCatalogCategoryHandler, Depends(get_set_default_catalog_category_handler)
]


def get_list_catalog_categories_handler(uow: UoWDep) -> ListCatalogCategoriesHandler:
    """Собирает зависимости сценария в общем tenant UoW."""
    return ListCatalogCategoriesHandler(
        SqlAlchemyCatalogCategoryQueryRepository(uow.session)
    )


ListCatalogCategoriesHandlerDep = Annotated[
    ListCatalogCategoriesHandler, Depends(get_list_catalog_categories_handler)
]
