from typing import Any
from collections.abc import Mapping
from src.modules.catalog.infrastructure.persistence.models.content_block_translation import (
    ContentBlockTranslationModel,
)
from src.modules.catalog.infrastructure.content_block.persistence.content_block_translations import (
    read_content_block_translations,
)
from sqlalchemy import select, func, or_, cast, String
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.content_block.value_object.identifier import (
    ContentBlockIdVO,
)
from src.modules.catalog.infrastructure.content_block.persistence.query_mapper import (
    ContentBlockQueryMapper,
)
from src.modules.catalog.infrastructure.persistence.models.content_block import (
    ContentBlockModel,
)
from src.modules.catalog.application.content_block.query.get_content_block.dto import (
    GetContentBlockDetailsDTO,
)
from src.modules.catalog.application.content_block.query.list_content_blocks.dto import (
    ListContentBlocksPageDTO,
)


class SqlAlchemyContentBlockQueryRepository:
    """Читает SQL-проекции в уже выбранной tenant-схеме."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию внешнего UoW."""
        self._session = session

    async def get_details(
        self, identifier: ContentBlockIdVO, locale: str
    ) -> GetContentBlockDetailsDTO | None:
        """Возвращает карточку и null при отсутствии перевода выбранной locale."""
        row = (
            (
                await self._session.execute(
                    select(ContentBlockModel.__table__).where(
                        ContentBlockModel.id == identifier.uuid
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        return ContentBlockQueryMapper.to_details(await self._projection(row), locale)

    async def list_page(
        self, locale: str, search: str, page: int, page_size: int
    ) -> ListContentBlocksPageDTO:
        """Читает страницу и total с одинаковыми серверными фильтрами."""
        statement = select(ContentBlockModel.__table__)
        if search:
            escaped = (
                search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            )
            statement = statement.where(
                or_(
                    select(ContentBlockTranslationModel.content_block_id)
                    .where(
                        ContentBlockTranslationModel.content_block_id
                        == ContentBlockModel.id,
                        ContentBlockTranslationModel.locale == locale,
                        ContentBlockTranslationModel.label.ilike(
                            "%" + escaped + "%", escape="\\"
                        ),
                    )
                    .exists()
                    | ContentBlockModel.code.ilike("%" + escaped + "%", escape="\\"),
                    cast(ContentBlockModel.id, String).ilike(
                        "%" + escaped + "%", escape="\\"
                    ),
                )
            )
        total = await self._session.scalar(
            select(func.count()).select_from(statement.subquery())
        )
        rows = (
            (
                await self._session.execute(
                    statement.order_by(
                        ContentBlockModel.created_at.desc(), ContentBlockModel.id
                    )
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            )
            .mappings()
            .all()
        )
        items = tuple(
            [
                ContentBlockQueryMapper.to_list_item(
                    await self._projection(row), locale
                )
                for row in rows
            ]
        )
        return ListContentBlocksPageDTO(items, total or 0, page, page_size)

    async def _projection(self, row: Mapping[str, Any]) -> dict[str, Any]:
        """Собирает read-значения из структурированных таблиц без восстановления агрегата."""
        return {
            **row,
            "translations": await read_content_block_translations(
                self._session, row["id"]
            ),
        }
