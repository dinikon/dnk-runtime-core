from sqlalchemy import select, func, cast, String, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from src.modules.catalog.application.tag.query.get_tag.dto import GetTagDetailsDTO
from src.modules.catalog.application.tag.query.list_tags.dto import ListTagsPageDTO
from src.modules.catalog.infrastructure.persistence.models.tag import TagModel
from src.modules.catalog.infrastructure.persistence.models.tag_translation import (
    TagTranslationModel,
)
from src.modules.catalog.infrastructure.tag.persistence.query_mapper import (
    TagQueryMapper,
)
from sqlalchemy.sql import Select


class SqlAlchemyTagQueryRepository:
    """Читает отдельные проекции справочника без восстановления агрегата."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает tenant-сессию общей транзакции."""
        self._session = session

    @staticmethod
    def _statement() -> Select:
        """Готовит техническую проекцию с числом дочерних узлов."""
        statement = select(TagModel.__table__)
        return statement

    async def get_details(
        self, identifier: TagIdVO, locale: str
    ) -> GetTagDetailsDTO | None:
        """Возвращает детали и явные локали либо отсутствие объекта."""
        row = (
            (
                await self._session.execute(
                    self._statement().where(TagModel.id == identifier.uuid)
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        labels = dict(
            (
                await self._session.execute(
                    select(TagTranslationModel.locale, TagTranslationModel.label).where(
                        TagTranslationModel.tag_id == identifier.uuid
                    )
                )
            ).all()
        )
        return TagQueryMapper.to_details(row, labels, locale)

    async def list_page(
        self, locale: str, search: str, page: int, page_size: int
    ) -> ListTagsPageDTO:
        """Считает корни до пагинации с явным фильтром ветви и locale."""
        statement = (
            self._statement()
            .add_columns(TagTranslationModel.label)
            .outerjoin(
                TagTranslationModel,
                (TagTranslationModel.tag_id == TagModel.id)
                & (TagTranslationModel.locale == locale),
            )
        )
        if search:
            escaped = (
                search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            statement = statement.where(
                or_(
                    TagTranslationModel.label.ilike("%" + escaped + "%", escape="\\"),
                    cast(TagModel.id, String).ilike("%" + escaped + "%", escape="\\"),
                )
            )
        total = await self._session.scalar(
            select(func.count()).select_from(statement.subquery())
        )
        rows = (
            (
                await self._session.execute(
                    statement.order_by(TagModel.created_at, TagModel.id)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .mappings()
            .all()
        )
        return ListTagsPageDTO(
            tuple(TagQueryMapper.to_list_item(r) for r in rows),
            total or 0,
            page,
            page_size,
        )
