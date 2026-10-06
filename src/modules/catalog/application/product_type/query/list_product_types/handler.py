from src.modules.catalog.application.product_type.port.schema_reader import (
    ProductTypeSchemaReaderProtocol,
)
from src.modules.catalog.application.product_type.query.list_product_types.dto import (
    ProductTypeListItemDTO,
)
from src.modules.catalog.application.product_type.query.list_product_types.query import (
    ListProductTypesQuery,
)


class ListProductTypesHandler:
    def __init__(self, reader: ProductTypeSchemaReaderProtocol) -> None:
        self._reader = reader

    async def execute(
        self, query: ListProductTypesQuery
    ) -> tuple[ProductTypeListItemDTO, ...]:
        return tuple(
            ProductTypeListItemDTO(
                item.id,
                item.code,
                item.is_system,
                item.schema_version,
                item.translations,
                item.blocks,
            )
            for item in await self._reader.list_types()
        )
