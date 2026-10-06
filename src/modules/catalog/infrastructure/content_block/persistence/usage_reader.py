from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
)
from src.modules.catalog.infrastructure.persistence.models.product_content_value import (
    ProductContentValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.variant_content_value import (
    VariantContentValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type_content_block import (
    ProductTypeContentBlockModel,
)


class SqlAlchemyContentBlockUsageReader:
    """Проверяет ссылки на определение блока в общей транзакции."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_in_use(self, block_id: ContentBlockIdVO) -> bool:
        for model in (
            ProductTypeContentBlockModel,
            ProductContentValueModel,
            VariantContentValueModel,
        ):
            if await self._session.scalar(
                select(exists().where(model.block_id == block_id.uuid))
            ):
                return True
        return False
