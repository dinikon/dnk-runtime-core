from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.channels.domain.sync_run.aggregate import SyncRun
from src.modules.channels.domain.error import ChannelsNotFoundError
from src.modules.channels.infrastructure.persistence.models.sync_run import SyncRunModel
from src.modules.channels.infrastructure.sync_run.persistence.mapper import (
    SyncRunMapper,
)


class SqlAlchemySyncRunRepository:
    """Сохраняет run, полагаясь на внешний UoW и порядок Channel → run."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает сессию общей транзакции."""
        self.session = session

    async def channel_id(self, identifier: EntityIdVO) -> EntityIdVO:
        """Читает owner ID без блокировки run для правильного порядка locks."""
        value = await self.session.scalar(
            select(SyncRunModel.channel_id).where(SyncRunModel.id == identifier.uuid)
        )
        if value is None:
            raise ChannelsNotFoundError("initialization_not_found")
        return EntityIdVO(value)

    async def get(self, identifier: EntityIdVO) -> SyncRun:
        """Загружает и блокирует run после владельца Channel."""
        row = (
            (
                await self.session.execute(
                    select(SyncRunModel.__table__)
                    .where(SyncRunModel.id == identifier.uuid)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ChannelsNotFoundError("initialization_not_found")
        return SyncRunMapper.to_domain(row)

    async def latest(self, connection_id: EntityIdVO) -> SyncRun | None:
        """Находит последний запуск под уже удерживаемой блокировкой Channel."""
        row = (
            (
                await self.session.execute(
                    select(SyncRunModel.__table__)
                    .where(SyncRunModel.connection_id == connection_id.uuid)
                    .order_by(SyncRunModel.created_at.desc(), SyncRunModel.id.desc())
                    .limit(1)
                    .with_for_update()
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else SyncRunMapper.to_domain(row)

    async def by_request(
        self, connection_id: EntityIdVO, request_key: EntityIdVO
    ) -> SyncRun | None:
        """Находит уже принятый idempotency key в текущем Connection."""
        row = (
            (
                await self.session.execute(
                    select(SyncRunModel.__table__).where(
                        SyncRunModel.connection_id == connection_id.uuid,
                        SyncRunModel.request_keys.contains([str(request_key)]),
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        return None if row is None else SyncRunMapper.to_domain(row)

    async def add(self, run: SyncRun) -> None:
        """Вставляет run без commit."""
        await self.session.execute(
            insert(SyncRunModel).values(**SyncRunMapper.to_values(run))
        )

    async def save(self, run: SyncRun) -> None:
        """Сохраняет run без commit."""
        await self.session.execute(
            update(SyncRunModel)
            .where(SyncRunModel.id == run.id.uuid)
            .values(**SyncRunMapper.to_values(run))
        )
