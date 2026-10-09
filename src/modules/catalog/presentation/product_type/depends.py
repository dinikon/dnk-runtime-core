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
    SchemaServiceDep,
)
from src.modules.catalog.application.product_type.port.query_repository import (
    ProductTypeQueryRepositoryProtocol,
)
from src.modules.catalog.infrastructure.product_type.persistence.query_repository import (
    SqlAlchemyProductTypeQueryRepository,
)
from src.modules.catalog.application.product_type.command.create_product_type.handler import (
    CreateProductTypeHandler,
)
from src.modules.catalog.application.product_type.command.delete_product_type.handler import (
    DeleteProductTypeHandler,
)
from src.modules.catalog.application.product_type.command.put_product_type_translation.handler import (
    PutProductTypeTranslationHandler,
)
from src.modules.catalog.application.product_type.command.replace_product_type_schema.handler import (
    ReplaceProductTypeSchemaHandler,
)
from src.modules.catalog.application.product_type.query.get_product_type.handler import (
    GetProductTypeHandler,
)
from src.modules.catalog.application.product_type.query.list_product_types.handler import (
    ListProductTypesHandler,
)


def get_query_repository(uow: UoWDep) -> ProductTypeQueryRepositoryProtocol:
    """Собирает read repository текущего корня на tenant-сессии."""
    return SqlAlchemyProductTypeQueryRepository(uow.session)


QueryRepositoryDep = Annotated[
    ProductTypeQueryRepositoryProtocol, Depends(get_query_repository)
]


def get_create_product_type_handler(
    repository: ProductTypeRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    uuid: UuidDep,
    schemas: SchemaServiceDep,
    locales: LocalesDep,
) -> CreateProductTypeHandler:
    """Собирает конкретный сценарий create_product_type из необходимых портов."""
    return CreateProductTypeHandler(
        repository=repository,
        lock=lock,
        clock=clock,
        uuid=uuid,
        schemas=schemas,
        locales=locales,
    )


CreateProductTypeHandlerDep = Annotated[
    CreateProductTypeHandler, Depends(get_create_product_type_handler)
]


def get_delete_product_type_handler(
    repository: ProductTypeRepositoryDep, lock: MutationLockDep
) -> DeleteProductTypeHandler:
    """Собирает конкретный сценарий delete_product_type из необходимых портов."""
    return DeleteProductTypeHandler(repository=repository, lock=lock)


DeleteProductTypeHandlerDep = Annotated[
    DeleteProductTypeHandler, Depends(get_delete_product_type_handler)
]


def get_put_product_type_translation_handler(
    repository: ProductTypeRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    locales: LocalesDep,
) -> PutProductTypeTranslationHandler:
    """Собирает конкретный сценарий put_product_type_translation из необходимых портов."""
    return PutProductTypeTranslationHandler(
        repository=repository, lock=lock, clock=clock, locales=locales
    )


PutProductTypeTranslationHandlerDep = Annotated[
    PutProductTypeTranslationHandler, Depends(get_put_product_type_translation_handler)
]


def get_replace_product_type_schema_handler(
    repository: ProductTypeRepositoryDep,
    lock: MutationLockDep,
    clock: ClockDep,
    schemas: SchemaServiceDep,
    products: ProductRepositoryDep,
) -> ReplaceProductTypeSchemaHandler:
    """Собирает конкретный сценарий replace_product_type_schema из необходимых портов."""
    return ReplaceProductTypeSchemaHandler(
        repository=repository,
        lock=lock,
        clock=clock,
        schemas=schemas,
        products=products,
    )


ReplaceProductTypeSchemaHandlerDep = Annotated[
    ReplaceProductTypeSchemaHandler, Depends(get_replace_product_type_schema_handler)
]


def get_get_product_type_handler(
    lock: MutationLockDep,
    repository: QueryRepositoryDep,
) -> GetProductTypeHandler:
    """Собирает конкретный сценарий get_product_type из необходимых портов."""
    return GetProductTypeHandler(repository=repository, lock=lock)


GetProductTypeHandlerDep = Annotated[
    GetProductTypeHandler, Depends(get_get_product_type_handler)
]


def get_list_product_types_handler(
    lock: MutationLockDep,
    repository: QueryRepositoryDep,
) -> ListProductTypesHandler:
    """Собирает конкретный сценарий list_product_types из необходимых портов."""
    return ListProductTypesHandler(repository=repository, lock=lock)


ListProductTypesHandlerDep = Annotated[
    ListProductTypesHandler, Depends(get_list_product_types_handler)
]
