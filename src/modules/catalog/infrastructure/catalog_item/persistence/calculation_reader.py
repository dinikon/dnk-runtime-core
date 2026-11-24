from datetime import datetime
from decimal import Decimal
from typing import cast
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.application.catalog_item.port.calculation_reader import (
    CatalogCalculationReference,
    CatalogCalculationSnapshot,
    CatalogCalculationItemNotFoundError,
    CatalogCalculationRequestError,
    CatalogPublicationValues,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item import (
    CatalogItemModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_category import (
    CatalogItemCategoryModel,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item_content_value import (
    CatalogItemContentValueModel,
)
from src.modules.catalog.infrastructure.persistence.models.content_block import (
    ContentBlockModel,
)
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
)
from src.modules.catalog.domain.catalog_item.policy.stock import resolve_stock
from src.modules.catalog.domain.catalog_item.value_object.stock import StockStatus
from src.modules.catalog.infrastructure.catalog_item.persistence.mapper import (
    CatalogItemMapper,
)


class SqlAlchemyCatalogCalculationReader:
    """Читает только выбранные записи одним SQL-снимком, не загружая всё семейство."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает tenant-сессию внешнего UoW без собственного commit."""
        self._session = session

    async def read_many(
        self, references: tuple[CatalogCalculationReference, ...], as_of: datetime
    ) -> tuple[CatalogCalculationSnapshot, ...]:
        """Проверяет роли/принадлежность и делегирует семантику акции Domain Catalog."""
        return await self._read(references, as_of, available_only=False)

    async def _read(
        self,
        references: tuple[CatalogCalculationReference, ...],
        as_of: datetime,
        *,
        available_only: bool,
    ) -> tuple[CatalogCalculationSnapshot, ...]:
        """Читает цены и категории одним запросом для пакета ссылок."""
        if len(references) > 100 or as_of.tzinfo is None or as_of.utcoffset() is None:
            raise CatalogCalculationRequestError(
                "Нужны ограниченный пакет и timezone-aware as_of."
            )
        identifiers: set[UUID] = set()
        for ref in references:
            if not isinstance(ref.item_id, UUID) or (
                ref.variant_id is not None and not isinstance(ref.variant_id, UUID)
            ):
                raise CatalogCalculationRequestError("Нужны UUID выбранных позиций.")
            identifiers.add(ref.item_id)
            if ref.variant_id is not None:
                identifiers.add(ref.variant_id)
        if not identifiers:
            return ()
        table = CatalogItemModel.__table__
        categories = CatalogItemCategoryModel.__table__
        category_ids = (
            select(func.array_agg(categories.c.category_id))
            .where(
                categories.c.catalog_item_id
                == func.coalesce(table.c.parent_id, table.c.id)
            )
            .correlate(table)
            .scalar_subquery()
        )
        rows = (
            await self._session.execute(
                select(
                    table.c.id,
                    table.c.parent_id,
                    table.c.kind,
                    table.c.sku,
                    table.c.manage_stock,
                    table.c.stock_quantity,
                    table.c.stock_status,
                    table.c.backorders,
                    table.c.status,
                    table.c.purchase_price,
                    category_ids.label("category_ids"),
                    table.c.revision,
                    table.c.regular_price,
                    table.c.sale_price,
                    table.c.date_on_sale_from,
                    table.c.date_on_sale_to,
                ).where(table.c.id.in_(identifiers))
            )
        ).mappings()
        indexed = {row["id"]: row for row in rows}
        result: list[CatalogCalculationSnapshot] = []
        for ref in references:
            root = indexed.get(ref.item_id)
            own = indexed.get(ref.variant_id or ref.item_id)
            if root is None or own is None or root["parent_id"] is not None:
                if available_only:
                    continue
                raise CatalogCalculationItemNotFoundError("Позиция Catalog не найдена.")
            valid = (
                root["kind"] == "simple"
                if ref.variant_id is None
                else root["kind"] == "variable"
                and own["kind"] == "variant"
                and own["parent_id"] == ref.item_id
            )
            if not valid:
                if available_only:
                    continue
                raise CatalogCalculationItemNotFoundError(
                    "Выберите самостоятельный товар либо принадлежащий родителю вариант."
                )
            if available_only and (
                root["status"] == "archived" or own["status"] == "archived"
            ):
                continue
            regular = cast(Decimal | None, own["regular_price"])
            specification = (
                PriceSpecificationVO(
                    regular,
                    cast(Decimal | None, own["sale_price"]),
                    cast(datetime | None, own["date_on_sale_from"]),
                    cast(datetime | None, own["date_on_sale_to"]),
                )
                if regular is not None
                else None
            )
            boundaries = (
                [
                    value
                    for value in (
                        specification.date_on_sale_from,
                        specification.date_on_sale_to,
                    )
                    if value is not None and value > as_of
                ]
                if specification is not None and specification.sale_price is not None
                else []
            )
            stock = resolve_stock(
                own=CatalogItemMapper.stock_from_row(own),
                parent=(
                    CatalogItemMapper.stock_from_row(root) if ref.variant_id else None
                ),
            ).specification
            result.append(
                CatalogCalculationSnapshot(
                    reference=ref,
                    selected_id=cast(UUID, own["id"]),
                    kind=cast(str, own["kind"]),
                    sku=cast(str | None, own["sku"]),
                    regular=regular,
                    sale=specification.active_sale(as_of) if specification else None,
                    effective=specification.at(as_of) if specification else None,
                    revision=cast(int, own["revision"]),
                    as_of=as_of,
                    valid_until=min(boundaries) if boundaries else None,
                    purchase=cast(Decimal | None, own["purchase_price"]),
                    stock_quantity=stock.stock_quantity,
                    in_stock=stock.effective_status() is StockStatus.IN_STOCK,
                    category_ids=tuple(
                        sorted(cast(list[UUID] | None, own["category_ids"]) or ())
                    ),
                )
            )
        return tuple(result)

    async def read_publication_values(
        self,
        references: tuple[CatalogCalculationReference, ...],
        as_of: datetime,
        locales: frozenset[str],
        content_codes: frozenset[str],
    ) -> tuple[CatalogPublicationValues, ...]:
        """Читает эффективный контент пакетом с учётом явной очистки у варианта."""
        calculations = await self._read(references, as_of, available_only=True)
        if not calculations or not locales or not content_codes:
            return tuple(CatalogPublicationValues(c, ()) for c in calculations)
        identifiers = {
            identifier
            for calculation in calculations
            for identifier in (calculation.reference.item_id, calculation.selected_id)
        }
        content = CatalogItemContentValueModel.__table__
        blocks = ContentBlockModel.__table__
        rows = await self._session.execute(
            select(
                content.c.catalog_item_id,
                content.c.locale,
                blocks.c.code,
                content.c.value,
            )
            .join(blocks, blocks.c.id == content.c.block_id)
            .where(
                content.c.catalog_item_id.in_(identifiers),
                content.c.locale.in_(locales),
                blocks.c.code.in_(content_codes),
            )
        )
        values: dict[tuple[UUID, str, str], str | None] = {
            (identifier, locale, code): value
            for identifier, locale, code, value in rows
        }
        return tuple(
            CatalogPublicationValues(
                calculation,
                tuple(
                    (
                        code,
                        locale,
                        values.get(
                            (calculation.selected_id, locale, code),
                            values.get((calculation.reference.item_id, locale, code)),
                        ),
                    )
                    for locale in sorted(locales)
                    for code in sorted(content_codes)
                ),
            )
            for calculation in calculations
        )
