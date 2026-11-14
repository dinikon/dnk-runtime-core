from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.inventory.domain.packaging_type.deletion_usage import (
    PackagingTypeDeletionUsage,
)
from src.modules.inventory.domain.packaging_type.value_object.identifier import (
    PackagingTypeIdVO,
)
from src.modules.inventory.infrastructure.persistence.models.item_packaging import (
    ItemPackagingModel,
)


class SqlAlchemyPackagingTypeUsage:
    """Читает наличие ссылок из упаковок без загрузки или блокировки InventoryItem."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает ту же tenant-сессию, что используется для блокировки и удаления типа."""
        self._session = session

    async def get(self, identifier: PackagingTypeIdVO) -> PackagingTypeDeletionUsage:
        """Выполняет типизированный EXISTS по индексу ссылки независимо от активности."""
        statement = select(
            select(ItemPackagingModel.id)
            .where(ItemPackagingModel.packaging_type_id == identifier.uuid)
            .exists()
        )
        result = await self._session.execute(statement)
        return PackagingTypeDeletionUsage(has_item_packagings=result.scalar_one())
