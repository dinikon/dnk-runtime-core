from sqlalchemy import delete, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.catalog.domain.content_block.aggregate import ContentBlockDefinition
from src.modules.catalog.domain.content_block.value_object.content_block import (
    ContentBlockIdVO,
)
from src.modules.catalog.infrastructure.content_block.persistence.mapper import (
    ContentBlockMapper,
)
from src.modules.catalog.infrastructure.persistence.models.content_block_definition import (
    ContentBlockDefinitionModel,
)
from src.modules.catalog.infrastructure.persistence.models.content_block_translation import (
    ContentBlockTranslationModel,
)


class SqlAlchemyContentBlockRepository:
    """Сохраняет корень ContentBlockDefinition в общей tenant-транзакции."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_for_update(
        self, block_id: ContentBlockIdVO
    ) -> ContentBlockDefinition | None:
        row = (
            await self._session.execute(
                select(ContentBlockDefinitionModel)
                .where(ContentBlockDefinitionModel.id == block_id.uuid)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        translations = (
            (
                await self._session.execute(
                    select(ContentBlockTranslationModel).where(
                        ContentBlockTranslationModel.block_id == block_id.uuid
                    )
                )
            )
            .scalars()
            .all()
        )
        return ContentBlockMapper.to_domain(row, list(translations))

    async def add(self, block: ContentBlockDefinition) -> None:
        await self._session.execute(
            insert(ContentBlockDefinitionModel).values(
                ContentBlockMapper.to_insert_values(block)
            )
        )
        await self._write_translations(block)

    async def save(self, block: ContentBlockDefinition) -> None:
        await self._session.execute(
            update(ContentBlockDefinitionModel)
            .where(ContentBlockDefinitionModel.id == block.id.uuid)
            .values(type=block.type.value)
        )
        await self._session.execute(
            delete(ContentBlockTranslationModel).where(
                ContentBlockTranslationModel.block_id == block.id.uuid
            )
        )
        await self._write_translations(block)

    async def _write_translations(self, block: ContentBlockDefinition) -> None:
        await self._session.execute(
            insert(ContentBlockTranslationModel),
            ContentBlockMapper.to_translation_values(block),
        )

    async def delete(self, block: ContentBlockDefinition) -> None:
        await self._session.execute(
            delete(ContentBlockDefinitionModel).where(
                ContentBlockDefinitionModel.id == block.id.uuid
            )
        )
