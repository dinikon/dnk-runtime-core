from typing import Annotated

from fastapi import Depends

from src.modules.catalog.application.product.command.create_product.handler import (
    CreateProductHandler,
)
from src.modules.catalog.application.product.command.create_variable_product.handler import (
    CreateVariableProductHandler,
)
from src.modules.catalog.application.product.command.create_variant.handler import (
    CreateVariantHandler,
)
from src.modules.catalog.application.product.command.put_variant.handler import (
    PutVariantHandler,
)
from src.modules.catalog.application.product.command.delete_variant.handler import (
    DeleteVariantHandler,
)
from src.modules.catalog.application.product.command.put_variant_structure.handler import (
    PutVariantStructureHandler,
)
from src.modules.catalog.application.product.command.put_variant_content.handler import (
    PutVariantContentHandler,
)
from src.modules.catalog.application.product.command.delete_product.handler import (
    DeleteProductHandler,
)
from src.modules.catalog.application.product.query.get_variant.handler import (
    GetVariantHandler,
)
from src.modules.catalog.application.product.query.list_products.handler import (
    ListProductsHandler,
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


def get_list_products_handler(
    repository: ProductQueryRepositoryDep,
) -> ListProductsHandler:
    return ListProductsHandler(repository)


ListProductsHandlerDep = Annotated[
    ListProductsHandler, Depends(get_list_products_handler)
]


def get_delete_product_handler(
    repository: ProductRepositoryDep,
) -> DeleteProductHandler:
    return DeleteProductHandler(repository)


DeleteProductHandlerDep = Annotated[
    DeleteProductHandler, Depends(get_delete_product_handler)
]


def get_create_variable_product_handler(
    repository: ProductRepositoryDep,
    skus: SkuReaderDep,
    locales: LocaleReaderDep,
    clock: ClockDep,
    uuids: UuidDep,
) -> CreateVariableProductHandler:
    return CreateVariableProductHandler(repository, skus, locales, clock, uuids)


CreateVariableProductHandlerDep = Annotated[
    CreateVariableProductHandler, Depends(get_create_variable_product_handler)
]


def get_put_variant_structure_handler(
    repository: ProductRepositoryDep,
    skus: SkuReaderDep,
    clock: ClockDep,
    uuids: UuidDep,
) -> PutVariantStructureHandler:
    return PutVariantStructureHandler(repository, skus, clock, uuids)


PutVariantStructureHandlerDep = Annotated[
    PutVariantStructureHandler, Depends(get_put_variant_structure_handler)
]


def get_create_variant_handler(
    repository: ProductRepositoryDep,
    skus: SkuReaderDep,
    clock: ClockDep,
    uuids: UuidDep,
) -> CreateVariantHandler:
    return CreateVariantHandler(repository, skus, clock, uuids)


CreateVariantHandlerDep = Annotated[
    CreateVariantHandler, Depends(get_create_variant_handler)
]


def get_put_variant_handler(
    repository: ProductRepositoryDep, skus: SkuReaderDep, clock: ClockDep
) -> PutVariantHandler:
    return PutVariantHandler(repository, skus, clock)


PutVariantHandlerDep = Annotated[PutVariantHandler, Depends(get_put_variant_handler)]


def get_delete_variant_handler(
    repository: ProductRepositoryDep, clock: ClockDep
) -> DeleteVariantHandler:
    return DeleteVariantHandler(repository, clock)


DeleteVariantHandlerDep = Annotated[
    DeleteVariantHandler, Depends(get_delete_variant_handler)
]


def get_put_variant_content_handler(
    repository: ProductRepositoryDep, locales: LocaleReaderDep, clock: ClockDep
) -> PutVariantContentHandler:
    return PutVariantContentHandler(repository, locales, clock)


PutVariantContentHandlerDep = Annotated[
    PutVariantContentHandler, Depends(get_put_variant_content_handler)
]


def get_get_variant_handler(
    repository: ProductQueryRepositoryDep, skus: SkuReaderDep
) -> GetVariantHandler:
    return GetVariantHandler(repository, skus)


GetVariantHandlerDep = Annotated[GetVariantHandler, Depends(get_get_variant_handler)]
