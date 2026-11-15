from sqlalchemy import select, or_
from sqlalchemy.sql.elements import ColumnElement
from src.modules.inventory.application.accounting.filters import StockAccountingFilters
from src.modules.inventory.infrastructure.persistence.models.stock_positions import (
    StockPositionModel as P,
)
from src.modules.inventory.infrastructure.persistence.models.stock_location import (
    StockLocationModel as L,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel as I,
)
from src.modules.inventory.infrastructure.persistence.models.stock_lot import (
    StockLotModel as Lot,
)
from src.modules.inventory.infrastructure.persistence.models.stock_serial import (
    StockSerialModel as S,
)
from src.modules.inventory.infrastructure.persistence.models.stock_executions import (
    StockExecutionModel as E,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_lines import (
    StockExecutionLineModel as EL,
)
from src.modules.inventory.infrastructure.persistence.models.stock_postings import (
    StockPostingModel as T,
)
from src.modules.inventory.infrastructure.persistence.models.stock_ledger_entries import (
    StockLedgerEntryModel as Entry,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_ledger_links import (
    StockExecutionLedgerLinkModel as Link,
)


def dimension_filters(
    filters: StockAccountingFilters,
) -> tuple[ColumnElement[bool], ...]:
    """Строит общий фильтр позиций и Ledger через их неизменяемые измерения."""
    values: list[ColumnElement[bool]] = []
    for field, value in (
        (L.warehouse_id, filters.warehouse_id),
        (P.location_id, filters.location_id),
        (P.owner_id, filters.owner_id),
        (P.inventory_item_id, filters.inventory_item_id),
        (P.lot_id, filters.lot_id),
        (P.serial_id, filters.serial_id),
        (P.id, filters.position_id),
        (P.stock_status, filters.stock_status),
    ):
        if value is not None:
            values.append(field == value)
    if filters.search:
        values.append(
            or_(
                I.sku.icontains(filters.search, autoescape=True),
                Lot.number.icontains(filters.search, autoescape=True),
                S.number.icontains(filters.search, autoescape=True),
            )
        )
    return tuple(values)


def fact_filters(filters: StockAccountingFilters) -> tuple[ColumnElement[bool], ...]:
    """Связывает все фильтры детализации с одной фактической строкой без умножения заголовков."""
    values: list[ColumnElement[bool]] = []
    for field, value in (
        (E.warehouse_id, filters.warehouse_id),
        (E.owner_id, filters.owner_id),
        (E.document_id, filters.document_id),
        (E.id, filters.execution_id),
        (T.id, filters.posting_id),
        (E.operation_type, filters.operation_type),
    ):
        if value is not None:
            values.append(field == value)
    if filters.posted_from is not None:
        values.append(T.posted_at >= filters.posted_from)
    if filters.posted_to is not None:
        values.append(T.posted_at < filters.posted_to)
    line_filters: list[ColumnElement[bool]] = []
    for field, value in (
        (EL.inventory_item_id, filters.inventory_item_id),
        (EL.lot_id, filters.lot_id),
        (EL.serial_id, filters.serial_id),
        (EL.stock_status, filters.stock_status),
    ):
        if value is not None:
            line_filters.append(field == value)
    if filters.location_id is not None:
        line_filters.append(
            or_(
                EL.location_id == filters.location_id,
                EL.destination_location_id == filters.location_id,
            )
        )
    if filters.position_id is not None:
        line_filters.append(
            select(Link.execution_line_id)
            .join(Entry, Entry.id == Link.ledger_entry_id)
            .where(
                Link.execution_line_id == EL.id,
                Entry.position_id == filters.position_id,
            )
            .exists()
        )
    if filters.search:
        line_filters.append(
            or_(
                I.sku.icontains(filters.search, autoescape=True),
                Lot.number.icontains(filters.search, autoescape=True),
                S.number.icontains(filters.search, autoescape=True),
            )
        )
    if line_filters:
        values.append(
            select(EL.id)
            .join(I, I.id == EL.inventory_item_id)
            .outerjoin(Lot, Lot.id == EL.lot_id)
            .outerjoin(S, S.id == EL.serial_id)
            .where(EL.execution_id == E.id, *line_filters)
            .exists()
        )
    return tuple(values)
