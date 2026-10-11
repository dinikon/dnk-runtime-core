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
from src.modules.catalog.infrastructure.persistence.models.catalog_item_variant_selection import (
    CatalogItemVariantSelectionModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_default_selection import (
    CatalogItemDefaultSelectionModel,
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
    """Хранит семью в общей tenant-транзакции, сохраняя только изменённые части."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает внешнюю session и держит исходные строки для diff сохранения."""
        self._session = session
        self._original: dict[
            UUID, tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]
        ] = {}

    async def get(self, identifier: CatalogItemIdVO) -> CatalogItem:
        """Загружает только корень с принадлежащими детьми и восстанавливает семью."""
        table = CatalogItemModel.__table__
        rows = (
            (
                await self._session.execute(
                    select(table).where(
                        (table.c.id == identifier.uuid)
                        | (table.c.parent_id == identifier.uuid)
                    )
                )
            )
            .mappings()
            .all()
        )
        root = next(
            (r for r in rows if r["id"] == identifier.uuid and r["parent_id"] is None),
            None,
        )
        if root is None:
            raise CatalogNotFoundError("Корень CatalogItem отсутствует.")
        parts = await read_parts(self._session, tuple(r["id"] for r in rows))
        values = {r["id"]: CatalogItemMapper.to_values(r, parts) for r in rows}
        children = tuple(
            CatalogItemMapper.to_domain(values[r["id"]])
            for r in sorted(rows, key=lambda r: str(r["id"]))
            if r["parent_id"] == identifier.uuid
        )
        entity = CatalogItemMapper.to_domain(values[identifier.uuid], children)
        for item in (entity, *entity.children):
            self._original[item.id.uuid] = (
                CatalogItemMapper.to_insert_values(item),
                CatalogItemMapper.to_parts(item),
            )
        return entity

    async def add(self, entity: CatalogItem) -> None:
        """Добавляет корень и дочерние строки без самостоятельного commit."""
        await self.save(entity)

    async def save(self, entity: CatalogItem) -> None:
        """Синхронизирует diff агрегата; repo не вычисляет товарные правила."""
        items = (entity, *entity.children)
        current = {i.id.uuid for i in items}
        removed = {
            i
            for i, (row, _) in self._original.items()
            if row["parent_id"] == entity.id.uuid
        } - current
        if removed:
            await self._session.execute(
                delete(CatalogItemModel).where(CatalogItemModel.id.in_(removed))
            )
        for item in items:
            values = CatalogItemMapper.to_insert_values(item)
            before = self._original.get(item.id.uuid)
            if before is None:
                await self._session.execute(insert(CatalogItemModel).values(**values))
            else:
                changes = {k: v for k, v in values.items() if v != before[0][k]}
                if changes:
                    result = await self._session.execute(
                        update(CatalogItemModel)
                        .where(
                            CatalogItemModel.id == item.id.uuid,
                            CatalogItemModel.revision == before[0]["revision"],
                        )
                        .values(**changes)
                    )
                    if result.rowcount != 1:
                        raise CatalogConflictError("Конкурентная запись CatalogItem.")
        # First release removed selections/defaults, then changed axis links.
        for item in items:
            after = CatalogItemMapper.to_parts(item)
            before = self._original.get(item.id.uuid)
            old_parts = before[1] if before else {}
            for name in (
                "catalog_item_variant_selections",
                "catalog_item_default_selections",
            ):
                if old_parts.get(name, []) != after[name]:
                    model = (
                        CatalogItemVariantSelectionModel
                        if name.endswith("variant_selections")
                        else CatalogItemDefaultSelectionModel
                    )
                    await self._session.execute(
                        delete(model).where(model.catalog_item_id == item.id.uuid)
                    )
        for item in items:
            after = CatalogItemMapper.to_parts(item)
            before = self._original.get(item.id.uuid)
            await self._save_parts(item.id.uuid, before[1] if before else {}, after)
            self._original[item.id.uuid] = (
                CatalogItemMapper.to_insert_values(item),
                after,
            )
        for identifier in removed:
            self._original.pop(identifier, None)

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
        for model in (
            CatalogItemVariantSelectionModel,
            CatalogItemDefaultSelectionModel,
        ):
            if (
                before.get(model.__table__.name, []) != after[model.__table__.name]
                and after[model.__table__.name]
            ):
                await self._session.execute(insert(model), after[model.__table__.name])

    async def delete(self, entity: CatalogItem) -> None:
        """Удаляет уже проверенный корень с внутренними дочерними строками."""
        result = await self._session.execute(
            delete(CatalogItemModel).where(
                CatalogItemModel.id == entity.id.uuid,
                CatalogItemModel.revision == entity.revision,
            )
        )
        if result.rowcount != 1:
            raise CatalogConflictError("Конкурентная запись при удалении CatalogItem.")
