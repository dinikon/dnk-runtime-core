from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.channels.domain.product_representation.aggregate import (
    ProductRepresentation,
)
from src.modules.channels.domain.product_representation.error import (
    ProductRepresentationError,
)
from src.modules.channels.infrastructure.persistence.models.product_representation import (
    ProductRepresentationModel,
)
from src.modules.channels.infrastructure.product_representation.mapper import (
    ProductRepresentationMapper,
)
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlAlchemyProductRepresentationRepository:
    """Сохраняет корень под общей блокировкой Channel без управления UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию процесса, общую с репозиторием сопоставлений."""
        self._session = session

    async def get(self, binding_group_id: EntityIdVO) -> ProductRepresentation | None:
        """Блокирует существующую запись; отсутствие сериализуется блокировкой Channel."""
        table = ProductRepresentationModel.__table__
        row = (
            (
                await self._session.execute(
                    select(table)
                    .where(table.c.binding_group_id == binding_group_id.uuid)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        return ProductRepresentationMapper.to_domain(row) if row else None

    async def save(self, representation: ProductRepresentation) -> None:
        """Записывает только изменённую ревизию, не подменяя конфликт upsert-операцией."""
        table = ProductRepresentationModel.__table__
        revision = await self._session.scalar(
            select(table.c.revision).where(table.c.id == representation.id.uuid)
        )
        values = ProductRepresentationMapper.to_values(representation)
        if revision is None:
            await self._session.execute(insert(table).values(**values))
        elif revision != representation.revision:
            if revision != representation.revision - 1:
                raise ProductRepresentationError(
                    "representation_revision_conflict", conflict=True
                )
            result = await self._session.execute(
                update(table)
                .where(
                    table.c.id == representation.id.uuid, table.c.revision == revision
                )
                .values(**values)
            )
            if result.rowcount != 1:
                raise ProductRepresentationError(
                    "representation_revision_conflict", conflict=True
                )
