from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.channels.application.product_representation.contracts import (
    RepresentationBindingItem,
    RepresentationBindingSource,
)
from src.modules.channels.domain.catalog_binding.value_object import BindingMode
from src.modules.channels.infrastructure.persistence.models.catalog_binding_group import (
    CatalogBindingGroupModel,
)
from src.modules.channels.infrastructure.persistence.models.catalog_binding_item import (
    CatalogBindingItemModel,
)
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel,
)


class SqlAlchemyRepresentationQueryRepository:
    """Читает существующие таблицы Channels без нового хранения representation."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию общего tenant UoW без управления транзакцией."""
        self._session = session

    async def binding(
        self, *, channel_id: UUID, group_id: UUID
    ) -> RepresentationBindingSource | None:
        """Ограничивает группу каналом до чтения её пар; чужие ID дают None."""
        group = CatalogBindingGroupModel.__table__
        connection = ConnectionModel.__table__
        row = (
            (
                await self._session.execute(
                    select(group)
                    .join(connection, connection.c.id == group.c.connection_id)
                    .where(
                        group.c.id == group_id, connection.c.channel_id == channel_id
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        item = CatalogBindingItemModel.__table__
        pairs = (
            (
                await self._session.execute(
                    select(item)
                    .where(item.c.group_id == group_id)
                    .order_by(item.c.catalog_position_id, item.c.id)
                )
            )
            .mappings()
            .all()
        )
        return RepresentationBindingSource(
            id=row["id"],
            connection_id=row["connection_id"],
            catalog_root_id=row["catalog_root_id"],
            mode=BindingMode(row["mode"]),
            publication_root_id=row["publication_root_id"],
            revision=row["revision"],
            items=tuple(
                RepresentationBindingItem(
                    value["id"], value["catalog_position_id"], value["publication_id"]
                )
                for value in pairs
            ),
        )
