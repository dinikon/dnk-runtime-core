from typing import Annotated
from fastapi import Depends
from src.modules.catalog.presentation.catalog_item.depends import SchemasDep
from src.modules.catalog.application.product_type.query.get_default_product_type.handler import (
    GetDefaultProductTypeHandler,
)


def get_default_product_type_handler(
    schemas: SchemasDep,
) -> GetDefaultProductTypeHandler:
    """Собирает единственный read сценарий системной схемы."""
    return GetDefaultProductTypeHandler(schemas)


GetDefaultProductTypeHandlerDep = Annotated[
    GetDefaultProductTypeHandler, Depends(get_default_product_type_handler)
]
