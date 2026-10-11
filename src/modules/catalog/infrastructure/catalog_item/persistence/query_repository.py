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
from src.modules.catalog.infrastructure.persistence.models.catalog_item_category import (
    CatalogItemCategoryModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_tag import (
    CatalogItemTagModel,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.mapper import (
    CatalogItemMapper,
)
from src.modules.catalog.infrastructure.catalog_item.persistence.rows import read_parts
from src.modules.catalog.infrastructure.catalog_item.content_schema import (
    SqlAlchemyDefaultContentSchema,
)
from src.modules.catalog.domain.catalog_item.value_object.kind import CatalogItemKind
from src.modules.catalog.domain.catalog_item.value_object.stock import (
    BackorderPolicy,
    StockStatus,
)
from src.modules.catalog.domain.catalog_item.policy.effective_values import (
    CatalogItemEffectiveValuesPolicy,
)
from src.modules.catalog.domain.product_type.value_object.schema import BLOCK_IDS
from src.modules.catalog.domain.error import (
    CatalogNotFoundError,
    CatalogConflictError,
    InvalidCatalogValueError,
)
from src.modules.catalog.application.catalog_item.read_dto import CatalogItemReadDTO
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
from src.modules.catalog.application.catalog_item.query.list_catalog_item_variants.query import (
    ListCatalogItemVariantsQuery,
)
from src.modules.catalog.application.catalog_item.query.list_catalog_item_variants.dto import (
    ListCatalogItemVariantsResultDTO,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_items_publication_snapshot.query import (
    GetCatalogItemsPublicationSnapshotQuery,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_items_publication_snapshot.dto import (
    GetCatalogItemsPublicationSnapshotResultDTO,
)


class SqlAlchemyCatalogItemQueryRepository:
    """Batch read проекции на REPEATABLE READ session внешней сборки."""

    def __init__(self, session: AsyncSession) -> None:
        """Не восстанавливает Domain Aggregate и не управляет UoW."""
        self._session = session

    async def _project(
        self, rows: Sequence[Mapping[str, Any]], locale: str, as_of: datetime
    ) -> tuple[CatalogItemReadDTO, ...]:
        """Читает связанные таблицы по набору ID, независимо от размера страницы."""
        if not rows:
            return ()
        table = CatalogItemModel.__table__
        selected = {r["id"]: r for r in rows}
        parents = {
            r["parent_id"] for r in rows if r["parent_id"] is not None
        } - selected.keys()
        all_rows = dict(selected)
        if parents:
            parent_rows = (
                (
                    await self._session.execute(
                        select(table).where(table.c.id.in_(parents))
                    )
                )
                .mappings()
                .all()
            )
            all_rows.update({r["id"]: r for r in parent_rows})
        parts = await read_parts(self._session, tuple(all_rows), locale)
        values = {
            identifier: CatalogItemMapper.to_values(row, parts)
            for identifier, row in all_rows.items()
        }
        variables = tuple(r["id"] for r in rows if r["kind"] == "variable")
        children = []
        if variables:
            children = (
                (
                    await self._session.execute(
                        select(table).where(table.c.parent_id.in_(variables))
                    )
                )
                .mappings()
                .all()
            )
        result = []
        for row in rows:
            own = values[row["id"]]
            effective = CatalogItemEffectiveValuesPolicy.resolve(
                own,
                values.get(own.parent_id.uuid if own.parent_id else None),
                locale,
                as_of,
            )
            price_currency = (
                effective.price_specification.currency
                if effective.price_specification
                else None
            )
            prices = []
            incomplete = False
            if own.kind == CatalogItemKind.VARIABLE:
                for child in children:
                    if (
                        child["parent_id"] != own.id.uuid
                        or child["status"] != "active"
                        or own.status != "active"
                    ):
                        continue
                    value = CatalogItemMapper.to_values(child, {})
                    child_effective = CatalogItemEffectiveValuesPolicy.resolve(
                        value, own, locale, as_of
                    )
                    price = child_effective.price
                    if child_effective.price_specification is not None:
                        price_currency = child_effective.price_specification.currency
                    if price is None:
                        incomplete = True
                    else:
                        prices.append(price)
            stock = effective.stock
            status = stock.effective_status() if stock else None
            result.append(
                CatalogItemReadDTO(
                    (own.parent_id or own.id).uuid,
                    (
                        values[own.parent_id.uuid].revision
                        if own.parent_id
                        else own.revision
                    ),
                    own,
                    effective,
                    status.value if status else None,
                    stock.backorders != BackorderPolicy.NO if stock else None,
                    status == StockStatus.ON_BACKORDER if stock else None,
                    min(prices) if prices else None,
                    max(prices) if prices else None,
                    incomplete,
                    price_currency,
                )
            )
        return tuple(result)

    async def get(
        self, query: GetCatalogItemQuery, as_of: datetime
    ) -> GetCatalogItemResultDTO:
        """Для VARIANT не читает соседние variants и их локализованный контент."""
        table = CatalogItemModel.__table__
        row = (
            (
                await self._session.execute(
                    select(table).where(table.c.id == query.item_id.uuid)
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise CatalogNotFoundError("CatalogItem отсутствует.")
        return GetCatalogItemResultDTO(
            (await self._project((row,), query.locale, as_of))[0], as_of
        )

    @staticmethod
    def _pagination(offset: int, limit: int) -> None:
        """Ограничивает размер batch и неотрицательное смещение."""
        if offset < 0 or not 1 <= limit <= 100:
            raise InvalidCatalogValueError("Pagination: offset>=0, limit 1..100.")

    async def list(
        self, query: ListCatalogItemsQuery, as_of: datetime
    ) -> ListCatalogItemsResultDTO:
        """Фильтрует до соединений, считает корни и загружает их страницу batch."""
        self._pagination(query.offset, query.limit)
        table = CatalogItemModel.__table__
        filters = []
        if query.parent_id is not None:
            filters.append(table.c.parent_id == query.parent_id)
        elif not query.include_variants:
            filters.append(table.c.parent_id.is_(None))
        if query.kind is not None:
            filters.append(table.c.kind == query.kind.value)
        if query.status is not None:
            filters.append(table.c.status == query.status.value)
        if query.search:
            content = CatalogItemContentValueModel.__table__
            name = (
                select(content.c.catalog_item_id)
                .where(
                    content.c.catalog_item_id == table.c.id,
                    content.c.locale == query.locale,
                    content.c.block_id == BLOCK_IDS["name"].uuid,
                    content.c.value.ilike("%" + query.search + "%"),
                )
                .exists()
            )
            filters.append(or_(table.c.sku.ilike("%" + query.search + "%"), name))
        if query.category_id:
            category = CatalogItemCategoryModel.__table__
            filters.append(
                select(category.c.catalog_item_id)
                .where(
                    category.c.catalog_item_id == table.c.id,
                    category.c.category_id == query.category_id,
                )
                .exists()
            )
        if query.tag_id:
            tag = CatalogItemTagModel.__table__
            filters.append(
                select(tag.c.catalog_item_id)
                .where(
                    tag.c.catalog_item_id == table.c.id, tag.c.tag_id == query.tag_id
                )
                .exists()
            )
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
        projected = await self._project(rows, query.locale, as_of)
        return ListCatalogItemsResultDTO(
            tuple(CatalogItemQueryMapper.list_row(item) for item in projected),
            total,
            query.offset,
            query.limit,
            as_of,
        )

    async def variants(
        self, query: ListCatalogItemVariantsQuery, as_of: datetime
    ) -> ListCatalogItemVariantsResultDTO:
        """Возвращает страницу детей существующего VARIABLE в стабильном порядке ID."""
        self._pagination(query.offset, query.limit)
        table = CatalogItemModel.__table__
        kind = await self._session.scalar(
            select(table.c.kind).where(table.c.id == query.root_id.uuid)
        )
        if kind is None:
            raise CatalogNotFoundError("Корень отсутствует.")
        if kind != "variable":
            raise InvalidCatalogValueError("Список вариантов принадлежит VARIABLE.")
        total = await self._session.scalar(
            select(func.count())
            .select_from(table)
            .where(table.c.parent_id == query.root_id.uuid)
        )
        rows = (
            (
                await self._session.execute(
                    select(table)
                    .where(table.c.parent_id == query.root_id.uuid)
                    .order_by(table.c.id)
                    .offset(query.offset)
                    .limit(query.limit)
                )
            )
            .mappings()
            .all()
        )
        return ListCatalogItemVariantsResultDTO(
            await self._project(rows, query.locale, as_of),
            total,
            query.offset,
            query.limit,
            as_of,
        )

    async def snapshot(
        self, query: GetCatalogItemsPublicationSnapshotQuery, as_of: datetime
    ) -> GetCatalogItemsPublicationSnapshotResultDTO:
        """Отдаёт согласованный batch контракт для адаптеров Channels."""
        if not 1 <= len(query.item_ids) <= 1000 or len(set(query.item_ids)) != len(
            query.item_ids
        ):
            raise InvalidCatalogValueError("Snapshot требует 1..1000 уникальных ID.")
        table = CatalogItemModel.__table__
        rows = (
            (
                await self._session.execute(
                    select(table).where(
                        table.c.id.in_(tuple(i.uuid for i in query.item_ids))
                    )
                )
            )
            .mappings()
            .all()
        )
        if len(rows) != len(query.item_ids):
            raise CatalogNotFoundError("Один из CatalogItem отсутствует.")
        by_id = {row["id"]: row for row in rows}
        items = await self._project(
            tuple(by_id[i.uuid] for i in query.item_ids), query.locale, as_of
        )
        for item in items:
            expected = (query.expected_root_revisions or {}).get(item.root_id)
            if expected is not None and expected != item.root_revision:
                raise CatalogConflictError("Source root revision изменена.")
        schema = await SqlAlchemyDefaultContentSchema(self._session).get_default()
        return GetCatalogItemsPublicationSnapshotResultDTO(
            items, schema, query.locale, as_of
        )
