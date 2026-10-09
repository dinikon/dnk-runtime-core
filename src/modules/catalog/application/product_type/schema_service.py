from src.modules.catalog.domain.product_type.repository import (
    ProductTypeRepositoryProtocol,
)
from src.modules.catalog.domain.content_block.repository import (
    ContentBlockRepositoryProtocol,
)
from src.modules.catalog.domain.product_type.value_object.identifier import (
    ProductTypeIdVO,
)
from src.modules.catalog.domain.product_type.value_object.block_link import (
    ProductTypeContentBlock,
)
from src.modules.catalog.domain.product.value_object.schema import (
    ProductSchemaSnapshot,
    ContentBlockSnapshot,
)


class ProductSchemaService:
    """Координирует чтение определений для immutable снимка доменной политики."""

    def __init__(
        self,
        types: ProductTypeRepositoryProtocol,
        blocks: ContentBlockRepositoryProtocol,
    ) -> None:
        """Принимает контракты самостоятельных корней без SQL-сессии."""
        self._types = types
        self._blocks = blocks

    async def from_links(
        self, links: tuple[ProductTypeContentBlock, ...]
    ) -> tuple[ContentBlockSnapshot, ...]:
        """Проверяет существование блоков и собирает их необходимые данные."""
        result = []
        for link in links:
            block = await self._blocks.get(link.block_id)
            result.append(
                ContentBlockSnapshot(
                    block.id, block.value_type, link.scope, link.required, link.position
                )
            )
        return tuple(result)

    async def get(self, identifier: ProductTypeIdVO) -> ProductSchemaSnapshot:
        """Возвращает текущую согласованную версию схемы."""
        entity = await self._types.get(identifier)
        return ProductSchemaSnapshot(
            entity.id, entity.schema_version, await self.from_links(entity.blocks)
        )
