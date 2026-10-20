import hashlib
from sqlalchemy import select, text, or_
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.channels.domain.content_update.aggregate import ContentUpdateRun
from src.modules.channels.domain.error import ChannelsNotFoundError
from src.modules.channels.infrastructure.persistence.models.content_update import (
    ContentUpdateRunModel as R,
)
from src.modules.channels.infrastructure.persistence.models.content_update_item import (
    ContentUpdateItemModel as I,
)
from src.modules.channels.infrastructure.content_update.persistence.mapper import (
    ContentUpdateMapper as Mapper,
)


class SqlAlchemyContentUpdateRepository:
    """Хранит операцию с позициями на общей сессии без внешних вызовов."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает tenant-сессию внешнего UoW."""
        self.session = session

    async def lock_scope(self, channel_id: EntityIdVO) -> None:
        """Сериализует подтверждение по каналу на срок короткой SQL-транзакции."""
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": int.from_bytes(channel_id.uuid.bytes[:8], signed=True)},
        )

    async def exists(self, identifier: EntityIdVO) -> bool:
        """Проверяет ключ идемпотентного создания."""
        return (
            await self.session.scalar(select(R.id).where(R.id == identifier.uuid))
            is not None
        )

    async def lock_request(self, identifier: EntityIdVO) -> None:
        """Защищает ключ подготовки до появления строки в SQL."""
        key = hashlib.sha256(
            ("content-update-request:" + str(identifier.uuid)).encode()
        ).digest()
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": int.from_bytes(key[:8], signed=True)},
        )

    async def get(self, identifier: EntityIdVO) -> ContentUpdateRun:
        """Загружает все позиции и восстанавливает корень под блокировкой."""
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
            raise ChannelsNotFoundError("content_update_not_found")
        items = (
            (
                await self.session.execute(
                    select(I.__table__)
                    .where(I.run_id == identifier.uuid)
                    .order_by(I.publication_id)
                )
            )
            .mappings()
            .all()
        )
        return Mapper.to_domain(row, items)

    async def busy(self, run: ContentUpdateRun) -> bool:
        """Не разрешает параллельные доставки к одной публикации."""
        return (
            await self.session.scalar(
                select(I.run_id)
                .join(R, R.id == I.run_id)
                .where(
                    R.id != run.id.uuid,
                    R.channel_id == run.channel_id.uuid,
                    or_(R.status.in_(("queued", "running")), I.status == "unknown"),
                    I.publication_id.in_(
                        tuple(item.publication_id.uuid for item in run.items)
                    ),
                )
                .limit(1)
            )
            is not None
        )

    async def save(self, run: ContentUpdateRun) -> None:
        """Сохраняет lifecycle и результаты; подтверждённые снимки не переписывает."""
        statement = insert(R).values(**Mapper.to_values(run))
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[R.id],
                set_={
                    key: getattr(statement.excluded, key)
                    for key in (
                        "status",
                        "revision",
                        "sequence",
                        "confirmed_at",
                        "preview_hash",
                    )
                },
            )
        )
        for item in run.items:
            statement = insert(I).values(**Mapper.item_values(run, item))
            await self.session.execute(
                statement.on_conflict_do_update(
                    index_elements=[I.run_id, I.publication_id],
                    set_={
                        key: getattr(statement.excluded, key)
                        for key in ("observed", "status", "issues", "attempts")
                    },
                )
            )
