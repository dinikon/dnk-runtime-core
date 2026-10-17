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
from src.modules.catalog.domain.product_type.value_object.schema import BLOCK_IDS
from src.modules.catalog.domain.error import (
    CatalogNotFoundError,
    CatalogConflictError,
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
from src.modules.catalog.application.catalog_item.query.get_catalog_items_publication_snapshot.query import (
    GetCatalogItemsPublicationSnapshotQuery,
)
from src.modules.catalog.application.catalog_item.query.get_catalog_items_publication_snapshot.dto import (
    GetCatalogItemsPublicationSnapshotResultDTO,
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
            await read_parts(self._session, tuple(r["id"] for r in rows), locale)
            if rows
            else {}
        )
        return tuple(CatalogItemMapper.to_values(row, parts) for row in rows)

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
                        table.c.kind == "simple",
                        table.c.parent_id.is_(None),
                    )
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise CatalogNotFoundError("CatalogItem отсутствует.")
        return GetCatalogItemResultDTO(
            CatalogItemQueryMapper.details(
                (await self._values((row,), query.locale))[0], query.locale, as_of
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
        filters = [table.c.kind == "simple", table.c.parent_id.is_(None)]
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
        values = await self._values(rows, query.locale)
        return ListCatalogItemsResultDTO(
            tuple(
                CatalogItemQueryMapper.list_row(item, query.locale, as_of)
                for item in values
            ),
            int(total or 0),
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
                        table.c.id.in_(tuple(i.uuid for i in query.item_ids)),
                        table.c.kind == "simple",
                        table.c.parent_id.is_(None),
                    )
                )
            )
            .mappings()
            .all()
        )
        if len(rows) != len(query.item_ids):
            raise CatalogNotFoundError("Один из CatalogItem отсутствует.")
        by_id = {row["id"]: row for row in rows}
        values = await self._values(
            tuple(by_id[i.uuid] for i in query.item_ids), query.locale
        )
        items = tuple(
            CatalogItemQueryMapper.publication(value, query.locale, as_of)
            for value in values
        )
        schema = await SqlAlchemyDefaultContentSchema(self._session).get_default()
        return GetCatalogItemsPublicationSnapshotResultDTO(
            items, schema, query.locale, as_of
        )
