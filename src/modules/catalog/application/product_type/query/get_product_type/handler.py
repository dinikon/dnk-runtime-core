from src.modules.catalog.application.product_type.port.schema_reader import (
    ProductTypeSchemaReaderProtocol,
)
from src.modules.catalog.application.product_type.query.get_product_type.dto import (
    ProductTypeDetailsDTO,
)
from src.modules.catalog.application.product_type.query.get_product_type.query import (
    GetProductTypeQuery,
)
from src.modules.catalog.domain.product_type.error import ProductTypeNotFoundError


class GetProductTypeHandler:
    def __init__(self, reader: ProductTypeSchemaReaderProtocol) -> None:
        self._reader = reader

    async def execute(self, query: GetProductTypeQuery) -> ProductTypeDetailsDTO:
        schema = await self._reader.get_type(query.type_id.uuid)
        if schema is None:
            raise ProductTypeNotFoundError("Product type not found.")
        return ProductTypeDetailsDTO(
            schema.id,
            schema.code,
            schema.is_system,
            schema.schema_version,
            schema.translations,
            schema.blocks,
        )
