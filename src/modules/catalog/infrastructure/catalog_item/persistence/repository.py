from src.modules.catalog.infrastructure.persistence.models.catalog_item_translation import (
    CatalogItemTranslationModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_content_value import (
    CatalogItemContentValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_gallery import (
    CatalogItemGalleryModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_image import (
    CatalogItemImageModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_attribute import (
    CatalogItemAttributeModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_attribute_option import (
    CatalogItemAttributeOptionModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_category import (
    CatalogItemCategoryModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_tag import (
    CatalogItemTagModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_metadata import (
    CatalogItemMetadataModel,
)

from collections.abc import Mapping
from typing import Any
from uuid import UUID
from sqlalchemy import select, insert, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.domain.catalog_item.aggregate import CatalogItem
from src.modules.catalog.domain.catalog_item.value_object.identifier import (
    CatalogItemIdVO,
)
from src.modules.catalog.domain.error import CatalogNotFoundError, CatalogConflictError
from src.modules.catalog.infrastructure.persistence.models.catalog_item import (
    CatalogItemModel,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.mapper import (
    CatalogItemMapper,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.rows import read_parts


class SqlAlchemyCatalogItemRepository:
    """Хранит товары в общей tenant-транзакции, сохраняя только изменённые части."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает внешнюю session и держит исходные строки для diff сохранения."""
        self._session = session
        self._original: dict[
            UUID, tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]
        ] = {}

    async def get(self, identifier: CatalogItemIdVO) -> CatalogItem:
        """Загружает только самостоятельный простой товар и его собственные связи."""
        table = CatalogItemModel.__table__
        row = (
            (
                await self._session.execute(
                    select(table).where(
                        table.c.id == identifier.uuid,
                        table.c.kind == "simple",
                        table.c.parent_id.is_(None),
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise CatalogNotFoundError("Товар отсутствует.")
        parts = await read_parts(self._session, (identifier.uuid,))
        entity = CatalogItemMapper.to_domain(CatalogItemMapper.to_values(row, parts))
        original_parts = CatalogItemMapper.to_parts(entity)
        # Старые clear означают отсутствие, но удаляются при следующем сохранении.
        for name in (
            "catalog_item_content_values",
            "catalog_item_attributes",
            "catalog_item_metadata",
        ):
            original_parts[name].extend(
                row for row in parts[name] if row["mode"] == "clear"
            )
        self._original[entity.id.uuid] = (
            CatalogItemMapper.to_insert_values(entity),
            original_parts,
        )
        return entity

    async def add(self, entity: CatalogItem) -> None:
        """Добавляет самостоятельный товар без собственного commit."""
        await self.save(entity)

    async def save(self, entity: CatalogItem) -> None:
        """Сохраняет изменённые поля и группы связей под блокировкой товара."""
        values = CatalogItemMapper.to_insert_values(entity)
        before = self._original.get(entity.id.uuid)
        if before is None:
            await self._session.execute(insert(CatalogItemModel).values(**values))
        else:
            changes = {
                key: value
                for key, value in values.items()
                if key != "revision" and value != before[0][key]
            }
            if changes:
                result = await self._session.execute(
                    update(CatalogItemModel)
                    .where(
                        CatalogItemModel.id == entity.id.uuid,
                        CatalogItemModel.kind == "simple",
                        CatalogItemModel.parent_id.is_(None),
                    )
                    .values(**changes)
                )
                if result.rowcount != 1:
                    raise CatalogConflictError("Конкурентная запись товара.")
        after = CatalogItemMapper.to_parts(entity)
        await self._save_parts(entity.id.uuid, before[1] if before else {}, after)
        self._original[entity.id.uuid] = (values, after)

    async def _save_parts(
        self,
        identifier: UUID,
        before: Mapping[str, list[dict[str, Any]]],
        after: Mapping[str, list[dict[str, Any]]],
    ) -> None:
        """Заменяет только изменённую группу внутренних связей в правильном порядке FK."""
        groups = (
            (CatalogItemContentValueModel, CatalogItemTranslationModel),
            (CatalogItemImageModel, CatalogItemGalleryModel),
            (CatalogItemAttributeOptionModel, CatalogItemAttributeModel),
            (CatalogItemMetadataModel,),
            (CatalogItemCategoryModel,),
            (CatalogItemTagModel,),
        )
        for models in groups:
            if all(
                before.get(m.__table__.name, []) == after[m.__table__.name]
                for m in models
            ):
                continue
            for model in models:
                await self._session.execute(
                    delete(model).where(model.catalog_item_id == identifier)
                )
            for model in reversed(models):
                rows = after[model.__table__.name]
                if rows:
                    await self._session.execute(insert(model), rows)

    async def delete(self, entity: CatalogItem) -> None:
        """Удаляет уже проверенный товар с его внутренними связями."""
        result = await self._session.execute(
            delete(CatalogItemModel).where(
                CatalogItemModel.id == entity.id.uuid,
                CatalogItemModel.kind == "simple",
                CatalogItemModel.parent_id.is_(None),
            )
        )
        if result.rowcount != 1:
            raise CatalogConflictError("Конкурентная запись при удалении CatalogItem.")
