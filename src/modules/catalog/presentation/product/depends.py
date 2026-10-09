from typing import Annotated
from fastapi import Depends
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.time.depends import ClockDep
from src.modules.shared.presentation.uuid.depends import UuidDep
from src.modules.catalog.presentation.depends.common import (
    ProductRepositoryDep,
    ProductTypeRepositoryDep,
    MutationLockDep,
    LocalesDep,
    SanitizerDep,
    SchemaServiceDep,
)
from src.modules.catalog.application.product.port.query_repository import (
    ProductQueryRepositoryProtocol,
)
from src.modules.catalog.infrastructure.product.persistence.query_repository import (
    SqlAlchemyProductQueryRepository,
)
from src.modules.catalog.application.product.command.create_simple_product.handler import (
    CreateSimpleProductHandler,
)
from src.modules.catalog.application.product.command.change_product_type.handler import (
    ChangeProductTypeHandler,
)
from src.modules.catalog.application.product.command.set_variant_properties.handler import (
    SetVariantPropertiesHandler,
)
from src.modules.catalog.application.product.command.put_product_content.handler import (
    PutProductContentHandler,
)
from src.modules.catalog.application.product.command.delete_product_content.handler import (
    DeleteProductContentHandler,
)
from src.modules.catalog.application.product.command.put_variant_content.handler import (
    PutVariantContentHandler,
)
from src.modules.catalog.application.product.command.delete_variant_content.handler import (
    DeleteVariantContentHandler,
)
from src.modules.catalog.application.product.command.delete_product.handler import (
    DeleteProductHandler,
)
from src.modules.catalog.application.product.query.get_product.handler import (
    GetProductHandler,
)
from src.modules.catalog.application.product.query.list_products.handler import (
    ListProductsHandler,
)
from src.modules.catalog.application.product.query.get_variant.handler import (
    GetVariantHandler,
)


def get_query_repository(uow: UoWDep) -> ProductQueryRepositoryProtocol:
    """Собирает read repository текущего корня на tenant-сессии."""
    return SqlAlchemyProductQueryRepository(uow.session)


QueryRepositoryDep = Annotated[
    ProductQueryRepositoryProtocol, Depends(get_query_repository)
]


def get_create_simple_product_handler(
    repository: ProductRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    uuid: UuidDep,
    schemas: SchemaServiceDep,
    types: ProductTypeRepositoryDep,
) -> CreateSimpleProductHandler:
    """Собирает конкретный сценарий create_simple_product из необходимых портов."""
    return CreateSimpleProductHandler(
        repository=repository,
        lock=lock,
        clock=clock,
        uuid=uuid,
        schemas=schemas,
        types=types,
    )


CreateSimpleProductHandlerDep = Annotated[
    CreateSimpleProductHandler, Depends(get_create_simple_product_handler)
]


def get_change_product_type_handler(
    repository: ProductRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    schemas: SchemaServiceDep,
) -> ChangeProductTypeHandler:
    """Собирает конкретный сценарий change_product_type из необходимых портов."""
    return ChangeProductTypeHandler(
        repository=repository, lock=lock, clock=clock, schemas=schemas
    )


ChangeProductTypeHandlerDep = Annotated[
    ChangeProductTypeHandler, Depends(get_change_product_type_handler)
]


def get_set_variant_properties_handler(
    repository: ProductRepositoryDep, lock: MutationLockDep, clock: ClockDep
) -> SetVariantPropertiesHandler:
    """Собирает конкретный сценарий set_variant_properties из необходимых портов."""
    return SetVariantPropertiesHandler(repository=repository, lock=lock, clock=clock)


SetVariantPropertiesHandlerDep = Annotated[
    SetVariantPropertiesHandler, Depends(get_set_variant_properties_handler)
]


def get_put_product_content_handler(
    repository: ProductRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    schemas: SchemaServiceDep,
    locales: LocalesDep,
    sanitizer: SanitizerDep,
) -> PutProductContentHandler:
    """Собирает конкретный сценарий put_product_content из необходимых портов."""
    return PutProductContentHandler(
        repository=repository,
        lock=lock,
        clock=clock,
        schemas=schemas,
        locales=locales,
        sanitizer=sanitizer,
    )


PutProductContentHandlerDep = Annotated[
    PutProductContentHandler, Depends(get_put_product_content_handler)
]


def get_delete_product_content_handler(
    repository: ProductRepositoryDep, lock: MutationLockDep, clock: ClockDep
) -> DeleteProductContentHandler:
    """Собирает конкретный сценарий delete_product_content из необходимых портов."""
    return DeleteProductContentHandler(repository=repository, lock=lock, clock=clock)


DeleteProductContentHandlerDep = Annotated[
    DeleteProductContentHandler, Depends(get_delete_product_content_handler)
]


def get_put_variant_content_handler(
    repository: ProductRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    schemas: SchemaServiceDep,
    locales: LocalesDep,
    sanitizer: SanitizerDep,
) -> PutVariantContentHandler:
    """Собирает конкретный сценарий put_variant_content из необходимых портов."""
    return PutVariantContentHandler(
        repository=repository,
        lock=lock,
        clock=clock,
        schemas=schemas,
        locales=locales,
        sanitizer=sanitizer,
    )


PutVariantContentHandlerDep = Annotated[
    PutVariantContentHandler, Depends(get_put_variant_content_handler)
]


def get_delete_variant_content_handler(
    repository: ProductRepositoryDep, lock: MutationLockDep, clock: ClockDep
) -> DeleteVariantContentHandler:
    """Собирает конкретный сценарий delete_variant_content из необходимых портов."""
    return DeleteVariantContentHandler(repository=repository, lock=lock, clock=clock)


DeleteVariantContentHandlerDep = Annotated[
    DeleteVariantContentHandler, Depends(get_delete_variant_content_handler)
]


def get_delete_product_handler(
    repository: ProductRepositoryDep, lock: MutationLockDep
) -> DeleteProductHandler:
    """Собирает конкретный сценарий delete_product из необходимых портов."""
    return DeleteProductHandler(repository=repository, lock=lock)


DeleteProductHandlerDep = Annotated[
    DeleteProductHandler, Depends(get_delete_product_handler)
]


def get_get_product_handler(
    repository: QueryRepositoryDep, lock: MutationLockDep
) -> GetProductHandler:
    """Собирает конкретный сценарий get_product из необходимых портов."""
    return GetProductHandler(repository=repository, lock=lock)


GetProductHandlerDep = Annotated[GetProductHandler, Depends(get_get_product_handler)]


def get_list_products_handler(
    repository: QueryRepositoryDep, lock: MutationLockDep
) -> ListProductsHandler:
    """Собирает конкретный сценарий list_products из необходимых портов."""
    return ListProductsHandler(repository=repository, lock=lock)


ListProductsHandlerDep = Annotated[
    ListProductsHandler, Depends(get_list_products_handler)
]


def get_get_variant_handler(
    repository: QueryRepositoryDep, lock: MutationLockDep
) -> GetVariantHandler:
    """Собирает конкретный сценарий get_variant из необходимых портов."""
    return GetVariantHandler(repository=repository, lock=lock)


GetVariantHandlerDep = Annotated[GetVariantHandler, Depends(get_get_variant_handler)]
