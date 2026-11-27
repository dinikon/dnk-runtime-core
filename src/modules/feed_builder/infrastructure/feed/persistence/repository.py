from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.feed_builder.application.feed.port.settings_repository import (
    LockedFeedSettings,
)
from src.modules.feed_builder.domain.feed.aggregate import Feed
from src.modules.feed_builder.domain.feed.value_object.feed_schema import FeedSchemaVO
from src.modules.feed_builder.domain.feed.value_object.feed_id import FeedIdVO
from src.modules.feed_builder.domain.feed.value_object.feed_version import FeedVersionVO
from src.modules.feed_builder.domain.feed.error import (
    FeedNotFoundError,
    FeedCodeConflictError,
    FeedVersionConflictError,
)
from src.modules.feed_builder.infrastructure.persistence.models.feed import FeedModel
from src.modules.feed_builder.infrastructure.feed.persistence.mapper import (
    FeedMapper,
    FeedSettingsValues,
    FeedRow,
)


def is_code_conflict(error: IntegrityError) -> bool:
    """Распознаёт только именованное ограничение кода, не скрывая остальные ошибки БД."""
    name = getattr(error.orig, "constraint_name", None)
    if name is None:
        name = getattr(getattr(error.orig, "__cause__", None), "constraint_name", None)
    return name == "uq_fb_feeds_code"


class SqlAlchemyFeedRepository:
    """Хранит агрегат в уже привязанной tenant-сессии внешнего UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает общую сессию без выбора схемы или открытия транзакции."""
        self._session = session

    async def add(self, feed: Feed) -> None:
        """Добавляет агрегат, переводя только конфликт кода в предметную ошибку."""
        try:
            await self._session.execute(
                insert(FeedModel).values(FeedMapper.to_insert_values(feed))
            )
        except IntegrityError as exc:
            if is_code_conflict(exc):
                raise FeedCodeConflictError("Код Feed уже занят.") from exc
            raise

    async def get_for_update(self, feed_id: FeedIdVO) -> Feed:
        """Блокирует строку текущего tenant и восстанавливает агрегат."""
        return FeedMapper.to_domain(await self._lock_row(feed_id))

    async def get_settings_for_update(self, feed_id: FeedIdVO) -> LockedFeedSettings:
        """Возвращает метаданные и сохранённый JSON без разбора нод."""
        row = await self._lock_row(feed_id)
        return LockedFeedSettings(
            FeedMapper.to_domain(row, schema=FeedSchemaVO()),
            row["schema_definition"],
        )

    async def _lock_row(self, feed_id: FeedIdVO) -> FeedRow:
        """Блокирует одну строку для обоих сценариев записи."""
        row = (
            await self._session.execute(
                select(FeedModel)
                .where(FeedModel.id == feed_id.uuid)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
        ).scalar_one_or_none()
        if row is None:
            raise FeedNotFoundError("Feed не найден.")
        return FeedMapper.row_values(row)

    async def save(self, feed: Feed, *, expected_version: FeedVersionVO) -> None:
        """Обновляет ожидаемую версию атомарно и не выполняет commit."""
        await self._save(feed, expected_version, FeedMapper.to_update_values(feed))

    async def save_settings(
        self, feed: Feed, *, expected_version: FeedVersionVO
    ) -> None:
        """Сохраняет версию и настройки без записи документа нод."""
        await self._save(feed, expected_version, FeedMapper.to_settings_values(feed))

    async def _save(
        self, feed: Feed, expected_version: FeedVersionVO, values: FeedSettingsValues
    ) -> None:
        """Выполняет один UPDATE через ожидаемую версию для обоих сценариев."""
        if feed.version.value != expected_version.value + 1:
            raise FeedVersionConflictError("Новая версия не следует за ожидаемой.")
        try:
            result = await self._session.execute(
                update(FeedModel)
                .where(
                    FeedModel.id == feed.id.uuid,
                    FeedModel.row_version == expected_version.value,
                )
                .values(values)
                .returning(FeedModel.id)
            )
        except IntegrityError as exc:
            if is_code_conflict(exc):
                raise FeedCodeConflictError("Код Feed уже занят.") from exc
            raise
        if result.scalar_one_or_none() is None:
            raise FeedVersionConflictError("Feed уже изменён.")
