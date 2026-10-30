from dataclasses import replace
from uuid import UUID
from src.modules.shared.domain.value_object.entity_id import EntityIdVO
from src.modules.catalog.domain.catalog_item.value_object.kind import CatalogItemKind
from src.modules.catalog.domain.catalog_item.policy.variant_values import (
    effective_variant,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_variant.query import (
    GetCatalogVariantQuery,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_variant.dto import (
    GetCatalogVariantResultDTO,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_variants.query import (
    ListCatalogVariantsQuery,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_variants.dto import (
    ListCatalogVariantsResultDTO,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_product_snapshot.query import (
    GetCatalogProductSnapshotQuery,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_product_snapshot.dto import (
    GetCatalogProductSnapshotResultDTO,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.query_mapper import (
    CatalogItemQueryMapper,
)
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.infrastructure.persistence.models.catalog_item import (
    CatalogItemModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_content_value import (
    CatalogItemContentValueModel,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.mapper import (
    CatalogItemMapper,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.rows import read_parts
from src.modules.catalog.infrastructure.persistence.models.content_block import (
    ContentBlockModel,
)
from src.modules.catalog.domain.error import (
    CatalogNotFoundError,
    InvalidCatalogValueError,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_item.query import (
    GetCatalogItemQuery,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_item.dto import (
    GetCatalogItemResultDTO,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_items.query import (
    ListCatalogItemsQuery,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_items.dto import (
    ListCatalogItemsResultDTO,
)
from src.modules.catalog.domain.catalog_item.value_object.snapshot import (
    CatalogItemValuesSnapshot,
)


class SqlAlchemyCatalogItemQueryRepository:
    """Читает согласованные batch-проекции простых товаров на внешнем UoW."""

    def __init__(self, session: AsyncSession) -> None:
        """Не восстанавливает Domain Aggregate и не управляет UoW."""
        self._session = session

    async def _values(
        self, rows: Sequence[Mapping[str, Any]], locale: str
    ) -> tuple[CatalogItemValuesSnapshot, ...]:
        """Читает собственные связи одним запросом на группу, без родительских данных."""
        parts = (
            await read_parts(self._session, tuple((r["id"] for r in rows)), locale)
            if rows
            else {}
        )
        return tuple((CatalogItemMapper.to_values(row, parts) for row in rows))

    async def get(
        self, query: GetCatalogItemQuery, as_of: datetime
    ) -> GetCatalogItemResultDTO:
        """Читает детали самостоятельного простого товара выбранной locale."""
        table = CatalogItemModel.__table__
        row = (
            (
                await self._session.execute(
                    select(table).where(
                        table.c.id == query.item_id.uuid,
                        table.c.kind.in_(("simple", "variable")),
                        table.c.parent_id.is_(None),
                    )
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise CatalogNotFoundError("CatalogItem отсутствует.")
        root = (await self._values((row,), query.locale))[0]
        children = await self._child_values((row,), query.locale, include_parts=False)
        return GetCatalogItemResultDTO(
            CatalogItemQueryMapper.family_details(
                CatalogItemQueryMapper.details(root, query.locale, as_of),
                children,
                as_of,
            ),
            as_of,
        )

    @staticmethod
    def _pagination(offset: int, limit: int) -> None:
        """Ограничивает размер batch и неотрицательное смещение."""
        if offset < 0 or not 1 <= limit <= 100:
            raise InvalidCatalogValueError("Pagination: offset>=0, limit 1..100.")

    async def list(
        self, query: ListCatalogItemsQuery, as_of: datetime
    ) -> ListCatalogItemsResultDTO:
        """Фильтрует до соединений, считает товары и загружает их страницу batch."""
        self._pagination(query.offset, query.limit)
        table = CatalogItemModel.__table__
        filters = [
            table.c.kind.in_(("simple", "variable")),
            table.c.parent_id.is_(None),
        ]
        if query.kind is not None:
            if query.kind not in {"simple", "variable"}:
                raise InvalidCatalogValueError("Некорректный тип карточки.")
            filters.append(table.c.kind == query.kind)
        if query.status is not None:
            filters.append(table.c.status == query.status.value)
        if query.search:
            content = CatalogItemContentValueModel.__table__
            name = (
                select(content.c.catalog_item_id)
                .join(ContentBlockModel, ContentBlockModel.id == content.c.block_id)
                .where(
                    content.c.catalog_item_id == table.c.id,
                    content.c.locale == query.locale,
                    ContentBlockModel.code == "title",
                    content.c.value.ilike("%" + query.search + "%"),
                )
                .exists()
            )
            matches = (
                select(func.coalesce(table.c.parent_id, table.c.id))
                .where(or_(table.c.sku.ilike("%" + query.search + "%"), name))
                .correlate(None)
            )
            filters.append(table.c.id.in_(matches))
        total = await self._session.scalar(
            select(func.count()).select_from(table).where(*filters)
        )
        rows = (
            (
                await self._session.execute(
                    select(table)
                    .where(*filters)
                    .order_by(table.c.created_at.desc(), table.c.id)
                    .offset(query.offset)
                    .limit(query.limit)
                )
            )
            .mappings()
            .all()
        )
        values = await self._values(rows, query.locale)
        children = await self._child_values(rows, query.locale, include_parts=False)
        items = []
        for value in values:
            result = CatalogItemQueryMapper.list_row(value, query.locale, as_of)
            if value.kind is CatalogItemKind.VARIABLE:
                family = CatalogItemQueryMapper.family_details(
                    CatalogItemQueryMapper.details(value, query.locale, as_of),
                    tuple(v for v in children if v.parent_id == value.id),
                    as_of,
                )
                result = replace(
                    result,
                    variant_count=family.variant_count,
                    min_price=family.min_price,
                    max_price=family.max_price,
                    currency=family.currency,
                    mixed_currencies=family.mixed_currencies,
                )
            items.append(result)
        return ListCatalogItemsResultDTO(
            tuple(items),
            int(total or 0),
            query.offset,
            query.limit,
            as_of,
        )

    async def _root(self, identifier: UUID) -> Mapping[str, Any]:
        """Читает корень tenant-семьи без восстановления агрегата."""
        table = CatalogItemModel.__table__
        row = (
            (
                await self._session.execute(
                    select(table).where(
                        table.c.id == identifier,
                        table.c.parent_id.is_(None),
                        table.c.kind.in_(("simple", "variable")),
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise CatalogNotFoundError("Карточка отсутствует.")
        return row

    async def _child_values(
        self, roots: Sequence[Mapping[str, Any]], locale: str, include_parts: bool
    ) -> tuple[CatalogItemValuesSnapshot, ...]:
        """Получает детей всех корней одним SELECT и при необходимости batch частей."""
        if not roots:
            return ()
        table = CatalogItemModel.__table__
        types = {r["id"]: EntityIdVO(r["product_type_id"]) for r in roots}
        rows = (
            (
                await self._session.execute(
                    select(table)
                    .where(table.c.parent_id.in_(types))
                    .order_by(table.c.created_at, table.c.id)
                )
            )
            .mappings()
            .all()
        )
        parts = (
            await read_parts(self._session, tuple(r["id"] for r in rows), locale)
            if include_parts
            else {}
        )
        return tuple(
            CatalogItemMapper.to_values(row, parts, types[row["parent_id"]])
            for row in rows
        )

    async def get_variant(
        self, query: GetCatalogVariantQuery, as_of: datetime
    ) -> GetCatalogVariantResultDTO:
        """Разрешает принадлежность и источники полных данных одной позиции."""
        root = await self._root(query.item_id.uuid)
        if root["kind"] != "variable":
            raise CatalogNotFoundError("Вариант отсутствует в карточке.")
        table = CatalogItemModel.__table__
        row = (
            (
                await self._session.execute(
                    select(table).where(
                        table.c.id == query.variant_id.uuid,
                        table.c.parent_id == query.item_id.uuid,
                    )
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise CatalogNotFoundError("Вариант отсутствует в карточке.")
        parts = await read_parts(self._session, (root["id"], row["id"]), query.locale)
        parent = CatalogItemMapper.to_values(root, parts)
        own = CatalogItemMapper.to_values(row, parts, parent.product_type_id)
        return GetCatalogVariantResultDTO(
            CatalogItemQueryMapper.variant(parent, own, query.locale, as_of), as_of
        )

    async def list_variants(
        self, query: ListCatalogVariantsQuery, as_of: datetime
    ) -> ListCatalogVariantsResultDTO:
        """Пагинирует entity; значения наследования загружает пакетно для страницы."""
        self._pagination(query.offset, query.limit)
        root = await self._root(query.item_id.uuid)
        if root["kind"] != "variable":
            raise InvalidCatalogValueError("Простой товар не содержит вариантов.")
        table = CatalogItemModel.__table__
        total = await self._session.scalar(
            select(func.count())
            .select_from(table)
            .where(table.c.parent_id == root["id"])
        )
        rows = (
            (
                await self._session.execute(
                    select(table)
                    .where(table.c.parent_id == root["id"])
                    .order_by(table.c.created_at, table.c.id)
                    .offset(query.offset)
                    .limit(query.limit)
                )
            )
            .mappings()
            .all()
        )
        parts = await read_parts(
            self._session, (root["id"], *(r["id"] for r in rows)), query.locale
        )
        parent = CatalogItemMapper.to_values(root, parts)
        values = tuple(
            CatalogItemMapper.to_values(row, parts, parent.product_type_id)
            for row in rows
        )
        items = []
        for own in values:
            resolved = effective_variant(parent, own, query.locale)
            items.append(
                replace(
                    CatalogItemQueryMapper.list_row(
                        resolved.values,
                        query.locale,
                        as_of,
                    ),
                    status=own.status,
                    stock_source=(
                        "parent" if resolved.stock_source_id != own.id else "own"
                    ),
                )
            )
        return ListCatalogVariantsResultDTO(
            tuple(items), total or 0, query.offset, query.limit, as_of
        )

    async def get_snapshot(
        self, query: GetCatalogProductSnapshotQuery, as_of: datetime
    ) -> GetCatalogProductSnapshotResultDTO:
        """Передаёт публичный снимок без ORM и без платформенных идентичностей."""
        row = await self._root(query.item_id.uuid)
        parent = (await self._values((row,), query.locale))[0]
        children = await self._child_values((row,), query.locale, include_parts=True)
        root = CatalogItemQueryMapper.family_details(
            CatalogItemQueryMapper.details(parent, query.locale, as_of), children, as_of
        )
        variants = tuple(
            CatalogItemQueryMapper.variant(parent, own, query.locale, as_of)
            for own in children
        )
        return GetCatalogProductSnapshotResultDTO(root, variants, query.locale, as_of)

    async def snapshots(
        self, identifiers: tuple[UUID, ...], locale: str, as_of: datetime
    ) -> tuple[GetCatalogProductSnapshotResultDTO, ...]:
        """Читает семьи пакетно для публичного Application контракта."""
        if not identifiers:
            return ()
        table = CatalogItemModel.__table__
        rows = (
            (
                await self._session.execute(
                    select(table).where(
                        table.c.id.in_(identifiers),
                        table.c.parent_id.is_(None),
                        table.c.kind.in_(("simple", "variable")),
                    )
                )
            )
            .mappings()
            .all()
        )
        parents = await self._values(rows, locale)
        children = await self._child_values(rows, locale, include_parts=True)
        return tuple(
            GetCatalogProductSnapshotResultDTO(
                CatalogItemQueryMapper.family_details(
                    CatalogItemQueryMapper.details(parent, locale, as_of),
                    tuple(v for v in children if v.parent_id == parent.id),
                    as_of,
                ),
                tuple(
                    CatalogItemQueryMapper.variant(parent, v, locale, as_of)
                    for v in children
                    if v.parent_id == parent.id
                ),
                locale,
                as_of,
            )
            for parent in parents
        )
