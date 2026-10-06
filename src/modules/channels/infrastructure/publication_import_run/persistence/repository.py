from src.modules.channels.domain.channel.value_object.identifier import ChannelIdVO
from src.modules.channels.domain.publication_import_run.value_object.identifier import (
    PublicationImportRunIdVO,
)

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.domain.publication_import_run.aggregate import (
    PublicationImportRun,
)
from src.modules.channels.infrastructure.publication_import_run.persistence.mapper import (
    PublicationImportRunMapper,
)
from src.modules.channels.infrastructure.persistence.models.publication_import_run import (
    PublicationImportRunModel,
)


class SqlAlchemyPublicationImportRunRepository:
    """Хранит прогресс импорта без самостоятельного управления транзакцией."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию общего внешнего UoW."""
        self._session = session

    async def get(
        self, run_id: PublicationImportRunIdVO
    ) -> PublicationImportRun | None:
        """Блокирует запуск для короткого изменения его состояния."""
        table = PublicationImportRunModel.__table__
        row = (
            (
                await self._session.execute(
                    select(table).where(table.c.id == run_id.uuid).with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else PublicationImportRunMapper.to_domain(row)

    async def active(self, channel_id: ChannelIdVO) -> PublicationImportRun | None:
        """Читает незавершённый запуск под уже взятой сценарием блокировкой канала."""
        table = PublicationImportRunModel.__table__
        row = (
            (
                await self._session.execute(
                    select(table)
                    .where(
                        table.c.channel_id == channel_id.uuid,
                        table.c.status.in_(("queued", "running")),
                    )
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else PublicationImportRunMapper.to_domain(row)

    async def save(self, run: PublicationImportRun) -> None:
        """Записывает новое или обновлённое состояние запуска."""
        values = PublicationImportRunMapper.to_values(run)
        statement = insert(PublicationImportRunModel).values(**values)
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
