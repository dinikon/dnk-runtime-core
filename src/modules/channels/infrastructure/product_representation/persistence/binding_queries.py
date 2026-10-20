from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.application.product_representation.contracts import (
    CatalogBindingDTO,
)
from src.modules.channels.infrastructure.persistence.models.product_representation import (
    ProductRepresentationModel as R,
)
from src.modules.channels.infrastructure.persistence.models.external_binding import (
    ExternalBindingModel as B,
)


class SqlAlchemyBindingQueries:
    """Читает только собственные связи Channels, без SQL моделей Catalog."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает общий внешний UoW."""
        self.session = session

    async def active(self, publication_id: UUID) -> CatalogBindingDTO | None:
        """Находит единственную активную связь публикации."""
        row = (
            await self.session.execute(
                select(B.id).where(
                    B.publication_id == publication_id, B.released_at.is_(None)
                )
            )
        ).scalar_one_or_none()
        return await self.binding(row) if row else None

    async def binding(self, binding_id: UUID) -> CatalogBindingDTO | None:
        """Читает версию корня вместе с активностью конкретной связи."""
        row = (
            await self.session.execute(
                select(
                    B.id,
                    B.representation_id,
                    R.connection_id,
                    B.publication_id,
                    R.catalog_item_id,
                    R.revision,
                    B.released_at,
                )
                .join(R, R.id == B.representation_id)
                .where(B.id == binding_id)
            )
        ).one_or_none()
        return CatalogBindingDTO(*row[:6], row[6] is None) if row else None

    async def occupied(
        self, connection_id: UUID, item_ids: tuple[UUID, ...]
    ) -> frozenset[UUID]:
        """Отмечает занятые товары в результатах поиска одним batch SQL."""
        return frozenset(
            (
                await self.session.scalars(
                    select(R.catalog_item_id)
                    .join(B, B.representation_id == R.id)
                    .where(
                        R.connection_id == connection_id,
                        R.catalog_item_id.in_(item_ids),
                        B.released_at.is_(None),
                    )
                )
            ).all()
        )

    async def used_ids(self, item_ids: tuple[UUID, ...]) -> frozenset[UUID]:
        """Архив канала не снимает ссылки; учитывает только явное released_at."""
        return frozenset(
            (
                await self.session.scalars(
                    select(R.catalog_item_id)
                    .join(B, B.representation_id == R.id)
                    .where(R.catalog_item_id.in_(item_ids), B.released_at.is_(None))
                )
            ).all()
        )

    async def versions(
        self, connection_id: UUID, item_ids: tuple[UUID, ...]
    ) -> dict[UUID, int]:
        """Читает версии всех пар страницы одним SQL без Catalog joins."""
        return dict(
            (
                await self.session.execute(
                    select(R.catalog_item_id, R.revision).where(
                        R.connection_id == connection_id,
                        R.catalog_item_id.in_(item_ids),
                    )
                )
            ).all()
        )
