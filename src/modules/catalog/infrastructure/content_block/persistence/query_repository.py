from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.application.content_block.query.get_content_block.dto import (
    ContentBlockDetailsDTO,
)
from src.modules.catalog.application.content_block.query.list_content_blocks.dto import (
    ContentBlockListItemDTO,
)
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
    ContentBlockType,
)
from src.modules.catalog.infrastructure.persistence.models.content_block_definition import (
    ContentBlockDefinitionModel,
)
from src.modules.catalog.infrastructure.persistence.models.content_block_translation import (
    ContentBlockTranslationModel,
)


class SqlAlchemyContentBlockQueryRepository:
    """Читает проекции блоков без восстановления доменных корней."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, block_id: ContentBlockIdVO) -> ContentBlockDetailsDTO | None:
        rows = (
            await self._session.execute(
                select(ContentBlockDefinitionModel, ContentBlockTranslationModel)
                .outerjoin(
                    ContentBlockTranslationModel,
                    ContentBlockTranslationModel.block_id
                    == ContentBlockDefinitionModel.id,
                )
                .where(ContentBlockDefinitionModel.id == block_id.uuid)
                .order_by(ContentBlockTranslationModel.locale_code)
            )
        ).all()
        if not rows:
            return None
        block = rows[0][0]
        return ContentBlockDetailsDTO(
            block.id,
            block.code,
            ContentBlockType(block.type),
            block.is_system,
            {item.locale_code: item.name for _, item in rows if item is not None},
        )

    async def list(self) -> tuple[ContentBlockListItemDTO, ...]:
        rows = (
            await self._session.execute(
                select(ContentBlockDefinitionModel, ContentBlockTranslationModel)
                .outerjoin(
                    ContentBlockTranslationModel,
                    ContentBlockTranslationModel.block_id
                    == ContentBlockDefinitionModel.id,
                )
                .order_by(
                    ContentBlockDefinitionModel.code,
                    ContentBlockTranslationModel.locale_code,
                )
            )
        ).all()
        blocks: dict[UUID, ContentBlockListItemDTO] = {}
        for block, translation in rows:
            item = blocks.get(block.id)
            if item is None:
                item = ContentBlockListItemDTO(
                    block.id,
                    block.code,
                    ContentBlockType(block.type),
                    block.is_system,
                    {},
                )
                blocks[block.id] = item
            if translation is not None:
                item.translations[translation.locale_code] = translation.name
        return tuple(blocks.values())
