from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.product_representation.aggregate import (
    ProductRepresentation,
)
from src.modules.channels.domain.error import ChannelsNotFoundError
from src.modules.channels.infrastructure.persistence.models.product_representation import (
    ProductRepresentationModel as R,
)
from src.modules.channels.infrastructure.persistence.models.external_binding import (
    ExternalBindingModel as B,
)
from src.modules.channels.infrastructure.product_representation.persistence.mapper import (
    ProductRepresentationMapper as Mapper,
)


class SqlAlchemyProductRepresentationRepository:
    """Хранит корень и всю историю связей в одной внешней транзакции."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает tenant-сессию внешней сборки."""
        self.session = session

    async def get(self, identifier: EntityIdVO) -> ProductRepresentation:
        """Блокирует корень, затем восстанавливает его внутренние Entities."""
        row = (
            (
                await self.session.execute(
                    select(R.__table__).where(R.id == identifier.uuid).with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ChannelsNotFoundError("representation_not_found")
        bindings = (
            (
                await self.session.execute(
                    select(B.__table__)
                    .where(B.representation_id == identifier.uuid)
                    .order_by(B.created_at, B.id)
                )
            )
            .mappings()
            .all()
        )
        return Mapper.to_domain(row, bindings)

    async def find(
        self, connection_id: EntityIdVO, item_id: EntityIdVO
    ) -> ProductRepresentation | None:
        """Находит пару после захвата публичной блокировки Catalog item."""
        identifier = await self.session.scalar(
            select(R.id).where(
                R.connection_id == connection_id.uuid, R.catalog_item_id == item_id.uuid
            )
        )
        return await self.get(EntityIdVO(identifier)) if identifier else None

    async def save(self, representation: ProductRepresentation) -> None:
        """Записывает только состояние агрегата без commit и каскадных удалений."""
        statement = insert(R).values(**Mapper.to_values(representation))
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=["id"], set_={"revision": statement.excluded.revision}
            )
        )
        # Released bindings are applied first so the unique active index remains valid.
        for binding in sorted(
            representation.bindings, key=lambda b: b.released_at is None
        ):
            statement = insert(B).values(
                **Mapper.binding_values(representation, binding)
            )
            await self.session.execute(
                statement.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "released_at": statement.excluded.released_at,
                        "released_by": statement.excluded.released_by,
                    },
                )
            )
