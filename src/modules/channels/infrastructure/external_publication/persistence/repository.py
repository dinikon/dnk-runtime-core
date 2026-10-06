from src.modules.channels.domain.channel.value_object.identifier import ChannelIdVO
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.domain.external_publication.aggregate import (
    ExternalPublication,
)
from src.modules.channels.infrastructure.external_publication.persistence.mapper import (
    PublicationMapper,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel,
)


class SqlAlchemyPublicationRepository:
    """Сохраняет публикации текущего tenant на сессии внешнего UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает уже привязанную tenant-сессию."""
        self._session = session

    async def find(
        self,
        channel_id: ChannelIdVO,
        connection_revision: int,
        resource_type: str,
        external_id: str,
    ) -> ExternalPublication | None:
        """Читает исходный агрегат перед применением новой наблюдаемой ревизии."""
        table = ExternalPublicationModel.__table__
        row = (
            (
                await self._session.execute(
                    select(table).where(
                        table.c.channel_id == channel_id.uuid,
                        table.c.connection_revision == connection_revision,
                        table.c.resource_type == resource_type,
                        table.c.external_id == external_id,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else PublicationMapper.to_domain(row)

    async def save(self, publication: ExternalPublication) -> None:
        """Вставляет или обновляет снимок; сериализация канала выполняется сценарием."""
        values = PublicationMapper.to_values(publication)
        statement = insert(ExternalPublicationModel).values(**values)
        await self._session.execute(
            statement.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    key: value
                    for key, value in values.items()
                    if key not in ("id", "created_at")
                },
            )
        )
