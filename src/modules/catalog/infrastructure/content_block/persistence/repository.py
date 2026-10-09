from src.modules.catalog.infrastructure.content_block.persistence.content_block_translations import (
    read_content_block_translations,
    save_content_block_translations,
)
from sqlalchemy import select, insert, update, delete, exists
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.content_block.aggregate import ContentBlockDefinition
from src.modules.catalog.domain.content_block.value_object.identifier import (
    ContentBlockIdVO,
)
from src.modules.catalog.domain.content_block.error import ContentBlockNotFoundError
from src.modules.catalog.infrastructure.content_block.persistence.mapper import (
    ContentBlockMapper,
)
from src.modules.catalog.infrastructure.persistence.models.content_block import (
    ContentBlockModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_type_block import (
    ProductTypeBlockModel,
)


class SqlAlchemyContentBlockRepository:
    """Хранит агрегат на сессии общего tenant UoW; commit остаётся снаружи."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию с уже привязанной tenant-схемой."""
        self._session = session

    async def get(self, identifier: ContentBlockIdVO) -> ContentBlockDefinition:
        """Читает сохранённые части и восстанавливает агрегат через mapper."""
        result = await self._session.execute(
            select(ContentBlockModel.__table__).where(
                ContentBlockModel.id == identifier.uuid
            )
        )
        row = result.mappings().one_or_none()
        if row is None:
            raise ContentBlockNotFoundError("Объект отсутствует.")
        return ContentBlockMapper.to_domain(
            row,
            translations=await read_content_block_translations(
                self._session, identifier.uuid
            ),
        )

    async def add(self, entity: ContentBlockDefinition) -> None:
        """Добавляет все принадлежащие агрегату части без commit."""
        await self._session.execute(
            insert(ContentBlockModel).values(
                ContentBlockMapper.to_insert_values(entity)
            )
        )
        await save_content_block_translations(
            self._session, entity.id.uuid, entity.translations
        )

    async def save(self, entity: ContentBlockDefinition) -> None:
        """Сохраняет доменное состояние в текущей общей транзакции."""
        await self._session.execute(
            update(ContentBlockModel)
            .where(ContentBlockModel.id == entity.id.uuid)
            .values(ContentBlockMapper.to_update_values(entity))
        )
        await save_content_block_translations(
            self._session, entity.id.uuid, entity.translations
        )

    async def delete(self, entity: ContentBlockDefinition) -> None:
        """Удаляет агрегат после проверок Domain, без commit."""
        await self._session.execute(
            delete(ContentBlockModel).where(ContentBlockModel.id == entity.id.uuid)
        )

    async def is_used(self, identifier: ContentBlockIdVO) -> bool:
        """Проверяет использование блока в схемах; изменения сериализованы lock-портом."""
        return bool(
            await self._session.scalar(
                select(
                    exists().where(ProductTypeBlockModel.block_id == identifier.uuid)
                )
            )
        )
