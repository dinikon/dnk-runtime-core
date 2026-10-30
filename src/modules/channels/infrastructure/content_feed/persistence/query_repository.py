from uuid import UUID
from src.modules.channels.domain.content_feed.delivery import FeedDeliveryVO
from src.modules.channels.infrastructure.content_feed.delivery_document import (
    decode_delivery,
)
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from collections.abc import Mapping
from typing import Any
from src.modules.channels.application.content_feed.contracts import (
    FeedPublicationKey,
    FeedReadRow,
)
from src.modules.channels.domain.content_feed.error import ContentFeedError
from src.modules.channels.infrastructure.persistence.models.content_feed import (
    ContentFeedModel as F,
)
from src.modules.channels.infrastructure.persistence.models.connection import (
    ConnectionModel as C,
)
from src.modules.channels.infrastructure.persistence.models.catalog_binding_group import (
    CatalogBindingGroupModel as G,
)
from src.modules.channels.infrastructure.persistence.models.product_representation import (
    ProductRepresentationModel as R,
)
from src.modules.channels.infrastructure.persistence.models.external_publication import (
    ExternalPublicationModel as P,
)


class SqlAlchemyContentFeedQueryRepository:
    """Читает проекции области, не восстанавливая публикации или сопоставления."""

    def __init__(self, session: AsyncSession) -> None:
        """Использует сессию внешнего UoW."""
        self._session = session

    async def begin_snapshot(self) -> None:
        """Начинает новый read-этап после явного завершения предыдущего UoW этапа."""
        await self._session.execute(
            text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        )

    async def import_states(self, channel_id: UUID) -> tuple[FeedDeliveryVO, ...]:
        """Не восстанавливает настройки фидов для проверки их последней операции."""
        rows = (
            await self._session.execute(
                select(F.delivery_schema, F.delivery_state)
                .join(C, C.id == F.connection_id)
                .where(C.channel_id == channel_id)
            )
        ).all()
        return tuple(decode_delivery(schema, value) for schema, value in rows)

    async def channel_for_feed(self, feed_id: UUID) -> UUID:
        """Не ищет чужие схемы по публичному ID."""
        value = await self._session.scalar(
            select(C.channel_id).join(F, F.connection_id == C.id).where(F.id == feed_id)
        )
        if value is None:
            raise ContentFeedError("feed_not_found")
        return value

    async def groups(self, connection_id: UUID) -> tuple[UUID, ...]:
        """Не ограничивает исходный ассортимент списком разрешённых групп."""
        return tuple(
            (
                await self._session.scalars(
                    select(G.id)
                    .join(R, R.binding_group_id == G.id)
                    .where(G.connection_id == connection_id, R.export_enabled.is_(True))
                    .order_by(G.id)
                )
            ).all()
        )

    async def connection_id(self, channel_id: UUID) -> UUID:
        """Не восстанавливает Channel только ради идентификатора подключения."""
        identifier = await self._session.scalar(
            select(C.id).where(C.channel_id == channel_id)
        )
        if identifier is None:
            raise ContentFeedError("feed_channel_not_found")
        return identifier

    async def details(self, *, channel_id: UUID, feed_id: UUID) -> FeedReadRow:
        """Читает готовую проекцию карточки текущего канала."""
        row = (
            (
                await self._session.execute(
                    select(F.__table__)
                    .join(C, C.id == F.connection_id)
                    .where(C.channel_id == channel_id, F.id == feed_id)
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ContentFeedError("feed_not_found")
        return self._projection(row)

    async def list(self, channel_id: UUID) -> tuple[FeedReadRow, ...]:
        """Читает все карточки одним запросом."""
        rows = (
            (
                await self._session.execute(
                    select(F.__table__)
                    .join(C, C.id == F.connection_id)
                    .where(C.channel_id == channel_id)
                    .order_by(F.id)
                )
            )
            .mappings()
            .all()
        )
        return tuple(self._projection(row) for row in rows)

    @staticmethod
    def _projection(row: Mapping[str, Any]) -> FeedReadRow:
        """Явно отделяет поля проекции от SQLAlchemy row."""
        return FeedReadRow(
            row["id"],
            row["revision"],
            row["enabled"],
            row["scope_key"],
            row["source_schema"],
            row["source_settings"],
            row["access_token_encrypted"],
            row["created_at"],
            row["updated_at"],
        )

    async def publications(self, connection_id: UUID) -> tuple[FeedPublicationKey, ...]:
        """Возвращает непреобразованные строковые ключи обмена, включая ведущие нули."""
        rows = (
            await self._session.execute(
                select(P.id, P.revision, P.platform_data)
                .where(P.connection_id == connection_id)
                .order_by(P.id)
            )
        ).all()
        result = []
        for identifier, revision, data in rows:
            key = data.get("import_key")
            result.append(
                FeedPublicationKey(
                    identifier,
                    revision,
                    key if isinstance(key, str) and key.strip() else None,
                )
            )
        return tuple(result)
