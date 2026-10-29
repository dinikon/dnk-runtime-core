from src.modules.catalog.domain.catalog_item.entity.variant import CatalogVariant
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.infrastructure.catalog_item.content_schema import (
    SqlAlchemyProductTypeSchemas,
)
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
from collections.abc import Mapping
from typing import Any
from uuid import UUID
from sqlalchemy import select, insert, update, delete
from sqlalchemy.exc import IntegrityError
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
        self._families: dict[UUID, set[UUID]] = {}

    async def get(self, identifier: CatalogItemIdVO) -> CatalogItem:
        """Загружает корень и дочерние позиции пакетно со своими значениями."""
        table = CatalogItemModel.__table__
        row = (
            (
                await self._session.execute(
                    select(table).where(
                        table.c.id == identifier.uuid,
                        table.c.kind.in_(("simple", "variable")),
                        table.c.parent_id.is_(None),
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise CatalogNotFoundError("Товар отсутствует.")
        children = (
            (
                await self._session.execute(
                    select(table)
                    .where(table.c.parent_id == identifier.uuid)
                    .order_by(table.c.created_at, table.c.id)
                )
            )
            .mappings()
            .all()
        )
        identifiers = (identifier.uuid, *(child["id"] for child in children))
        parts = await read_parts(self._session, identifiers)
        schema = await SqlAlchemyProductTypeSchemas(self._session).get_by_id(
            EntityIdVO(row["product_type_id"])
        )
        variants = tuple(
            CatalogItemMapper.to_variant(
                CatalogItemMapper.to_values(child, parts, schema.id)
            )
            for child in children
        )
        entity = CatalogItemMapper.to_domain(
            CatalogItemMapper.to_values(row, parts), schema, variants
        )
        block_ids = {block.code: block.id.uuid for block in schema.blocks}
        for node in (entity, *entity.variants):
            original_parts = CatalogItemMapper.to_parts(node, block_ids)
            if isinstance(node, CatalogItem):
                original_parts["catalog_item_content_values"].extend(
                    r
                    for r in parts["catalog_item_content_values"]
                    if r["catalog_item_id"] == node.id.uuid and r["mode"] == "clear"
                )
            self._original[node.id.uuid] = (
                CatalogItemMapper.to_insert_values(node),
                original_parts,
            )
        self._families[identifier.uuid] = {child["id"] for child in children}
        return entity

    async def add(self, entity: CatalogItem) -> None:
        """Добавляет самостоятельный товар без собственного commit."""
        original, families = dict(self._original), dict(self._families)
        try:
            await self.save(entity)
        except BaseException:
            # Не оставляем кэш частично вставленной семьи после отказа INSERT.
            self._original, self._families = original, families
            raise

    async def save(self, entity: CatalogItem) -> None:
        """Сохраняет семью атомарно, не записывая эффективные значения детям."""
        schema = await SqlAlchemyProductTypeSchemas(self._session).get_by_id(
            entity.product_type_id
        )
        remaining = {v.id.uuid for v in entity.variants}
        removed = self._families.get(entity.id.uuid, set()) - remaining
        if removed:
            await self._session.execute(
                delete(CatalogItemModel).where(
                    CatalogItemModel.parent_id == entity.id.uuid,
                    CatalogItemModel.id.in_(removed),
                )
            )
        for node in (entity, *entity.variants):
            await self._save_record(node, {b.code: b.id.uuid for b in schema.blocks})
        self._families[entity.id.uuid] = remaining

    async def _save_record(
        self, entity: CatalogItem | CatalogVariant, block_ids: Mapping[str, UUID]
    ) -> None:
        """Записывает только изменённую центральную строку и её собственные части."""
        values = CatalogItemMapper.to_insert_values(entity)
        before = self._original.get(entity.id.uuid)
        if before is None:
            try:
                await self._session.execute(insert(CatalogItemModel).values(**values))
            except IntegrityError as error:
                original = getattr(error.orig, "__cause__", None) or error.orig
                if getattr(original, "constraint_name", None) != "uq_catalog_item_sku":
                    raise
                raise CatalogConflictError(
                    "Конфликт уникального SKU.", ("sku",)
                ) from error
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
                        CatalogItemModel.kind == before[0]["kind"],
                        CatalogItemModel.parent_id == before[0]["parent_id"],
                    )
                    .values(**changes)
                )
                if result.rowcount != 1:
                    raise CatalogConflictError("Конкурентная запись товара.")
        after = CatalogItemMapper.to_parts(entity, block_ids)
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
        )
        for models in groups:
            if all(
                (
                    before.get(m.__table__.name, []) == after[m.__table__.name]
                    for m in models
                )
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
                CatalogItemModel.kind.in_(("simple", "variable")),
                CatalogItemModel.parent_id.is_(None),
            )
        )
        if result.rowcount != 1:
            raise CatalogConflictError("Конкурентная запись при удалении CatalogItem.")
