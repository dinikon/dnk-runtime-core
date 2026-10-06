from typing import Annotated

from fastapi import Depends

from src.modules.catalog.application.product_type.command.create_product_type.handler import (
    CreateProductTypeHandler,
)
from src.modules.catalog.application.product_type.command.delete_product_type.handler import (
    DeleteProductTypeHandler,
)
from src.modules.catalog.application.product_type.command.put_product_type.handler import (
    PutProductTypeHandler,
)
from src.modules.catalog.application.product_type.query.get_product_type.handler import (
    GetProductTypeHandler,
)
from src.modules.catalog.application.product_type.query.list_product_types.handler import (
    ListProductTypesHandler,
)
from src.modules.catalog.infrastructure.content_block.persistence.query_repository import (
    SqlAlchemyContentBlockQueryRepository,
)
from src.modules.catalog.infrastructure.product_type.persistence.repository import (
    SqlAlchemyProductTypeRepository,
)
from src.modules.catalog.infrastructure.product_type.persistence.schema_reader import (
    SqlAlchemyProductTypeSchemaReader,
)
from src.modules.catalog.infrastructure.product_type.persistence.usage_reader import (
    SqlAlchemyProductTypeUsageReader,
)
from src.modules.catalog.infrastructure.reference_locale_reader import (
    ReferenceLocaleReaderAdapter,
)
from src.modules.reference_data.infrastructure.persistence.repository import (
    SqlAlchemyCatalogRepository,
)
from src.modules.shared.presentation.persistence.depends import UoWDep
from src.modules.shared.presentation.uuid.depends import UuidDep


def get_create_product_type_handler(
    uow: UoWDep, uuids: UuidDep
) -> CreateProductTypeHandler:
    return CreateProductTypeHandler(
        SqlAlchemyProductTypeRepository(uow.session),
        SqlAlchemyContentBlockQueryRepository(uow.session),
        ReferenceLocaleReaderAdapter(SqlAlchemyCatalogRepository(uow.session)),
        uuids,
    )


CreateProductTypeHandlerDep = Annotated[
    CreateProductTypeHandler, Depends(get_create_product_type_handler)
]


def get_put_product_type_handler(uow: UoWDep) -> PutProductTypeHandler:
    return PutProductTypeHandler(
        SqlAlchemyProductTypeRepository(uow.session),
        SqlAlchemyContentBlockQueryRepository(uow.session),
        SqlAlchemyProductTypeUsageReader(uow.session),
        ReferenceLocaleReaderAdapter(SqlAlchemyCatalogRepository(uow.session)),
    )


PutProductTypeHandlerDep = Annotated[
    PutProductTypeHandler, Depends(get_put_product_type_handler)
]


def get_delete_product_type_handler(uow: UoWDep) -> DeleteProductTypeHandler:
    return DeleteProductTypeHandler(
        SqlAlchemyProductTypeRepository(uow.session),
        SqlAlchemyProductTypeUsageReader(uow.session),
    )


DeleteProductTypeHandlerDep = Annotated[
    DeleteProductTypeHandler, Depends(get_delete_product_type_handler)
]


def get_get_product_type_handler(uow: UoWDep) -> GetProductTypeHandler:
    return GetProductTypeHandler(SqlAlchemyProductTypeSchemaReader(uow.session))


GetProductTypeHandlerDep = Annotated[
    GetProductTypeHandler, Depends(get_get_product_type_handler)
]


def get_list_product_types_handler(uow: UoWDep) -> ListProductTypesHandler:
    return ListProductTypesHandler(SqlAlchemyProductTypeSchemaReader(uow.session))


ListProductTypesHandlerDep = Annotated[
    ListProductTypesHandler, Depends(get_list_product_types_handler)
]
