"""Хранение агрегатов внешних публикаций."""

from sqlalchemy import select, update, insert, or_, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.external_publication.aggregate import (
    ExternalPublication,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)
from src.modules.channels.infrastructure.external_publication.persistence.mapper import (
    to_domain,
    to_values,
)


class SqlAlchemyExternalPublicationRepository:
    """Загружает ограниченные наборы публикаций для применения страницы."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает общую tenant-сессию."""
        self.session = session

    async def by_keys(
        self, connection_id: EntityIdVO, keys: tuple[tuple[str, str], ...]
    ) -> tuple[ExternalPublication, ...]:
        """Загружает существующие снимки одним запросом."""
        if not keys:
            return ()
        model = ExternalPublicationModel
        rows = await self.session.scalars(
            select(model).where(
                model.connection_id == connection_id.uuid,
                tuple_(model.resource_type, model.external_id).in_(keys),
            )
        )
        return tuple(to_domain(row) for row in rows)

    async def affected_tree(
        self, connection_id: EntityIdVO, publication_ids: tuple[EntityIdVO, ...]
    ) -> tuple[ExternalPublication, ...]:
        """Читает изменяемые корни, их детей и существующих родителей."""
        if not publication_ids:
            return ()
        model = ExternalPublicationModel
        parents = select(model.parent_id).where(
            model.id.in_(item.uuid for item in publication_ids)
        )
        rows = await self.session.scalars(
            select(model).where(
                model.connection_id == connection_id.uuid,
                or_(
                    model.id.in_(item.uuid for item in publication_ids),
                    model.parent_id.in_(item.uuid for item in publication_ids),
                    model.id.in_(parents),
                    model.parent_id.in_(parents),
                ),
            )
        )
        return tuple(to_domain(row) for row in rows)

    async def save(self, publication: ExternalPublication) -> None:
        """Сохраняет валидированный агрегат без commit."""
        table = ExternalPublicationModel.__table__
        values = to_values(publication)
        result = await self.session.execute(
            update(table).where(table.c.id == publication.id.uuid).values(**values)
        )
        if result.rowcount == 0:
            await self.session.execute(insert(table).values(**values))

    async def next_variable_parent(
        self,
        connection_id: EntityIdVO,
        run_id: EntityIdVO,
        after: str | None,
        current: str | None,
    ) -> str | None:
        """Читает одного родителя из прохода текущего запуска."""
        model = ExternalPublicationModel
        statement = select(model.external_id).where(
            model.connection_id == connection_id.uuid,
            model.kind == "variable",
            model.last_sync_run_id == run_id.uuid,
        )
        if current is not None:
            statement = statement.where(model.external_id == current)
        elif after is not None:
            statement = statement.where(model.external_id > after)
        return await self.session.scalar(statement.order_by(model.external_id).limit(1))
