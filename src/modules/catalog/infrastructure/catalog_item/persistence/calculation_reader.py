from datetime import datetime
from decimal import Decimal
from typing import cast
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.catalog.application.catalog_item.port.calculation_reader import (
    CatalogCalculationReference,
    CatalogCalculationSnapshot,
    CatalogCalculationItemNotFoundError,
    CatalogCalculationRequestError,
)
from src.modules.catalog.infrastructure.persistence.models.catalog_item import (
    CatalogItemModel,
)
from src.modules.catalog.domain.catalog_item.value_object.price import (
    PriceSpecificationVO,
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
        rows = (
            await self._session.execute(
                select(
                    table.c.id,
                    table.c.parent_id,
                    table.c.kind,
                    table.c.sku,
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
                raise CatalogCalculationItemNotFoundError("Позиция Catalog не найдена.")
            valid = (
                root["kind"] == "simple"
                if ref.variant_id is None
                else root["kind"] == "variable"
                and own["kind"] == "variant"
                and own["parent_id"] == ref.item_id
            )
            if not valid:
                raise CatalogCalculationItemNotFoundError(
                    "Выберите самостоятельный товар либо принадлежащий родителю вариант."
                )
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
                )
            )
        return tuple(result)
