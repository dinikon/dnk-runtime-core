from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.tag.aggregate import Tag
from src.modules.catalog.domain.tag.value_object.identifier import TagIdVO
from src.modules.catalog.domain.tag.error import TagNotFoundError
from src.modules.catalog.infrastructure.persistence.models.tag import TagModel
from src.modules.catalog.infrastructure.persistence.models.tag_translation import (
    TagTranslationModel,
)
from src.modules.catalog.infrastructure.persistence.models.product_tag import (
    ProductTagModel,
)
from src.modules.catalog.infrastructure.tag.persistence.mapper import TagMapper


class SqlAlchemyTagRepository:
    """Хранит полный Tag на общей tenant-сессии внешнего UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию без управления schema и commit."""
        self._session = session

    async def get(self, identifier: TagIdVO) -> Tag:
        """Читает корень и переводы для доменного восстановления."""
        row = (
            (
                await self._session.execute(
                    select(TagModel.__table__).where(TagModel.id == identifier.uuid)
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise TagNotFoundError("Объект отсутствует.")
        labels = dict(
            (
                await self._session.execute(
                    select(TagTranslationModel.locale, TagTranslationModel.label).where(
                        TagTranslationModel.tag_id == identifier.uuid
                    )
                )
            ).all()
        )
        return TagMapper.to_domain(row, labels)

    async def add(self, entity: Tag) -> None:
        """Добавляет корень и его переводы без commit."""
        await self._session.execute(
            insert(TagModel).values(TagMapper.to_insert_values(entity))
        )
        await self._save_translations(entity)

    async def save(self, entity: Tag) -> None:
        """Сохраняет состояние, проверенное доменными методами."""
        await self._session.execute(
            update(TagModel)
            .where(TagModel.id == entity.id.uuid)
            .values(TagMapper.to_update_values(entity))
        )
        await self._save_translations(entity)

    async def _save_translations(self, entity: Tag) -> None:
        """Синхронизирует принадлежащие переводы в текущей транзакции."""
        await self._session.execute(
            delete(TagTranslationModel).where(
                TagTranslationModel.tag_id == entity.id.uuid
            )
        )
        if entity.translations:
            await self._session.execute(
                insert(TagTranslationModel),
                [
                    {"tag_id": entity.id.uuid, "locale": k, "label": v}
                    for k, v in entity.translations.items()
                ],
            )

    async def delete(self, entity: Tag) -> None:
        """Удаляет корень после проверки использования доменом."""
        await self._session.execute(
            delete(TagModel).where(TagModel.id == entity.id.uuid)
        )

    async def is_used(self, identifier: TagIdVO) -> bool:
        """Читает наличие назначений и дочерних узлов без бизнес-решения."""
        return bool(
            await self._session.scalar(
                select(ProductTagModel.product_id)
                .where(ProductTagModel.tag_id == identifier.uuid)
                .limit(1)
            )
        )
