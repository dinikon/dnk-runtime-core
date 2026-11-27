from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.feed_builder.application.access_key.query.list_feed_access_keys.dto import (
    FeedAccessKeyListItemDTO,
    ListFeedAccessKeysDTO,
)
from src.modules.feed_builder.infrastructure.persistence.models.access_key import (
    FeedAccessKeyModel as Key,
)
from src.modules.feed_builder.infrastructure.persistence.models.feed import (
    FeedModel as Feed,
)


class SqlAlchemyFeedAccessKeyListRepository:
    """Проецирует только видимые метаданные ключей."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает tenant-сессию чтения."""
        self._session = session

    async def list(
        self, feed_id: UUID, *, now: datetime
    ) -> ListFeedAccessKeysDTO | None:
        """Различает фид без ключей и отсутствующий фид одним запросом."""
        rows = (
            await self._session.execute(
                select(Key.id, Key.name, Key.created_at, Key.expires_at, Key.revoked_at)
                .select_from(Feed)
                .outerjoin(Key, Key.feed_id == Feed.id)
                .where(Feed.id == feed_id)
                .order_by(Key.created_at.desc(), Key.id.desc())
            )
        ).all()
        if not rows:
            return None
        return ListFeedAccessKeysDTO(
            tuple(
                FeedAccessKeyListItemDTO(
                    row.id,
                    row.name,
                    (
                        "REVOKED"
                        if row.revoked_at is not None
                        else (
                            "EXPIRED"
                            if row.expires_at is not None and row.expires_at <= now
                            else "ACTIVE"
                        )
                    ),
                    row.created_at,
                    row.expires_at,
                    row.revoked_at,
                )
                for row in rows
                if row.id is not None
            )
        )
