from typing import Annotated

from fastapi import Depends

from src.modules.catalog.application.product.command.create_product.handler import (
    CreateProductHandler,
)
from src.modules.catalog.application.product.command.put_product_content.handler import (
    PutProductContentHandler,
)
from src.modules.catalog.application.product.command.put_product_categories.handler import (
    PutProductCategoriesHandler,
)
from src.modules.catalog.application.product.port.category_reader import (
    CategoryReaderPort,
)
from src.modules.catalog.infrastructure.product.category_reader import (
    SqlAlchemyCategoryReader,
)
from src.modules.catalog.application.product.port.locale_reader import LocaleReaderPort
from src.modules.catalog.application.product.port.query_repository import (
    ProductQueryRepositoryProtocol,
)
from src.modules.catalog.application.product.port.sku_reader import SkuReaderPort
from src.modules.catalog.application.product.query.get_product.handler import (
    GetProductHandler,
)
from src.modules.catalog.domain.product.repository import ProductRepositoryProtocol
from src.modules.catalog.infrastructure.product.inventory_sku_reader import (
    InventorySkuReaderAdapter,
)
from src.modules.catalog.infrastructure.product.persistence.query_repository import (
    SqlAlchemyProductQueryRepository,
)
from src.modules.catalog.infrastructure.product.persistence.repository import (
    SqlAlchemyProductRepository,
)
from src.modules.catalog.infrastructure.reference_locale_reader import (
    ReferenceLocaleReaderAdapter,
)
from src.modules.inventory.infrastructure.sku.persistence.query_repository import (
    SqlAlchemySkuQueryRepository,
)
from src.modules.reference_data.infrastructure.persistence.repository import (
    SqlAlchemyCatalogRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_product_repository(uow: UoWDep) -> ProductRepositoryProtocol:
    return SqlAlchemyProductRepository(uow.session)


ProductRepositoryDep = Annotated[
    ProductRepositoryProtocol, Depends(get_product_repository)
]


def get_product_query_repository(uow: UoWDep) -> ProductQueryRepositoryProtocol:
    return SqlAlchemyProductQueryRepository(uow.session)


ProductQueryRepositoryDep = Annotated[
    ProductQueryRepositoryProtocol, Depends(get_product_query_repository)
]


def get_sku_reader(uow: UoWDep) -> SkuReaderPort:
    return InventorySkuReaderAdapter(SqlAlchemySkuQueryRepository(uow.session))


SkuReaderDep = Annotated[SkuReaderPort, Depends(get_sku_reader)]


def get_locale_reader(uow: UoWDep) -> LocaleReaderPort:
    return ReferenceLocaleReaderAdapter(SqlAlchemyCatalogRepository(uow.session))


LocaleReaderDep = Annotated[LocaleReaderPort, Depends(get_locale_reader)]


def get_create_product_handler(
    repository: ProductRepositoryDep,
    skus: SkuReaderDep,
    locales: LocaleReaderDep,
    clock: ClockDep,
    uuids: UuidDep,
) -> CreateProductHandler:
    return CreateProductHandler(repository, skus, locales, clock, uuids)


CreateProductHandlerDep = Annotated[
    CreateProductHandler, Depends(get_create_product_handler)
]


def get_get_product_handler(
    repository: ProductQueryRepositoryDep, skus: SkuReaderDep
) -> GetProductHandler:
    return GetProductHandler(repository, skus)


GetProductHandlerDep = Annotated[GetProductHandler, Depends(get_get_product_handler)]


def get_put_product_content_handler(
    repository: ProductRepositoryDep, locales: LocaleReaderDep, clock: ClockDep
) -> PutProductContentHandler:
    return PutProductContentHandler(repository, locales, clock)


PutProductContentHandlerDep = Annotated[
    PutProductContentHandler, Depends(get_put_product_content_handler)
]


def get_category_reader(uow: UoWDep) -> CategoryReaderPort:
    return SqlAlchemyCategoryReader(uow.session)


CategoryReaderDep = Annotated[CategoryReaderPort, Depends(get_category_reader)]


def get_put_product_categories_handler(
    repository: ProductRepositoryDep, categories: CategoryReaderDep, clock: ClockDep
) -> PutProductCategoriesHandler:
    return PutProductCategoriesHandler(repository, categories, clock)


PutProductCategoriesHandlerDep = Annotated[
    PutProductCategoriesHandler, Depends(get_put_product_categories_handler)
]
