from src.modules.channels.infrastructure.catalog_binding.mapper import (
    CatalogBindingMapper,
)
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.infrastructure.persistence.models.catalog_binding_group import (
    CatalogBindingGroupModel as G,
)
from src.modules.channels.infrastructure.persistence.models.catalog_binding_item import (
    CatalogBindingItemModel as I,
)
from src.modules.channels.domain.catalog_binding.aggregate import CatalogBindingGroup
from src.modules.shared.domain.value_object.entity_id import EntityIdVO


class SqlAlchemyCatalogBindingRepository:
    """Восстанавливает и сохраняет только агрегаты групп на внешнем UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Не владеет commit и не обращается к Catalog SQL."""
        self.session = session

    async def get(
        self,
        connection_id: EntityIdVO,
        group_id: EntityIdVO,
        *,
        for_update: bool = False,
    ) -> CatalogBindingGroup | None:
        """Восстанавливает Domain исключительно для mutations."""
        statement = select(G.__table__).where(
            G.id == group_id.uuid, G.connection_id == connection_id.uuid
        )
        if for_update:
            statement = statement.with_for_update()
        row = (await self.session.execute(statement)).mappings().one_or_none()
        if row is None:
            return None
        items = (
            (
                await self.session.execute(
                    select(I.__table__).where(I.group_id == group_id.uuid)
                )
            )
            .mappings()
            .all()
        )
        return CatalogBindingMapper.to_domain(row, items)

    async def save(self, group: CatalogBindingGroup) -> None:
        """Записывает собственные поля и полный набор пар атомарно."""
        values = CatalogBindingMapper.to_insert_values(group)
        before = await self.session.scalar(
            select(G.revision).where(G.id == group.id.uuid)
        )
        if before is None:
            await self.session.execute(insert(G).values(**values))
        elif before == group.revision:
            return
        else:
            await self.session.execute(
                update(G).where(G.id == group.id.uuid).values(**values)
            )
        existing = set(
            (
                await self.session.scalars(
                    select(I.id).where(I.group_id == group.id.uuid)
                )
            ).all()
        )
        current = {value.id.uuid for value in group.items}
        removed = existing - current
        if removed:
            await self.session.execute(
                delete(I).where(I.group_id == group.id.uuid, I.id.in_(removed))
            )
        added = [
            dict(
                id=v.id.uuid,
                group_id=group.id.uuid,
                catalog_position_id=v.catalog_position_id.uuid,
                publication_id=v.publication_id.uuid,
            )
            for v in group.items
            if v.id.uuid not in existing
        ]
        if added:
            await self.session.execute(insert(I), added)

    async def delete(self, group: CatalogBindingGroup) -> None:
        """Снимает группу, оставляя внешние и Catalog данные нетронутыми."""
        await self.session.execute(
            delete(G).where(
                G.id == group.id.uuid, G.connection_id == group.connection_id.uuid
            )
        )
