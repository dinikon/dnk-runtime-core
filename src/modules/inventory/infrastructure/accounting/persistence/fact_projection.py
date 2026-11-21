from src.modules.inventory.infrastructure.persistence.models.stock_execution_return import (
    StockExecutionReturnModel as ReturnDetails,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_return_line import (
    StockExecutionReturnLineModel as ReturnLine,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_status_change import (
    StockExecutionStatusChangeModel as StatusDetails,
)
from sqlalchemy import select, Nullable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased
from src.modules.inventory.infrastructure.persistence.models.stock_location import (
    StockLocationModel as L,
)
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel as W,
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
from src.modules.inventory.infrastructure.persistence.models.stock_document import (
    StockDocumentModel as D,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_line import (
    StockDocumentLineModel as DL,
)
from dataclasses import dataclass
from collections.abc import Sequence
from src.modules.inventory.infrastructure.persistence.models.stock_receipt_cost_evidence import (
    ReceiptCostEvidenceModel as Cost,
)
from src.modules.inventory.infrastructure.persistence.models.stock_receipt_cost_allocations import (
    ReceiptCostAllocationModel as Allocation,
)
from src.modules.inventory.infrastructure.persistence.models.stock_receipt_posting_requests import (
    ReceiptPostingRequestModel as Request,
)
from src.modules.inventory.infrastructure.stock_document.persistence.receipt_record_mapper import (
    ReceiptPostingRecordMapper,
)
from src.modules.inventory.application.stock_execution.query.get_stock_execution.dto import (
    GetStockExecutionResultDTO,
)
from uuid import UUID


@dataclass(frozen=True, slots=True)
class StockFactProjection:
    """Внутренняя типизированная SQL-проекция; ORM не покидает Infrastructure."""

    execution: E
    posting: T | None
    document: D
    warehouse: W
    lines: Sequence[tuple[EL, I, L, Lot | None, S | None, DL, L | None]]
    entries: Sequence[Entry]
    links: Sequence[Link]
    costs: Sequence[Cost]
    allocations: Sequence[Allocation]
    historical: GetStockExecutionResultDTO | None
    status_change: StatusDetails | None
    return_details: ReturnDetails | None
    return_lines: Sequence[ReturnLine]


class StockFactProjectionReader:
    """Читает неизменяемые части факта независимо от результата идемпотентной команды."""

    def __init__(self, session: AsyncSession) -> None:
        """Использует сессию внешней сборки."""
        self._session = session

    async def read(
        self, identifier: UUID, *, posting: bool
    ) -> StockFactProjection | None:
        """Пакетно читает нормализованные строки, Ledger, связи и стоимость без N+1."""
        statement = (
            select(
                E, Nullable(T), D, W, Nullable(StatusDetails), Nullable(ReturnDetails)
            )
            .outerjoin(ReturnDetails, ReturnDetails.execution_id == E.id)
            .outerjoin(StatusDetails, StatusDetails.execution_id == E.id)
            .outerjoin(T, T.execution_id == E.id)
            .join(D, D.id == E.document_id)
            .join(W, W.id == E.warehouse_id)
            .where(T.id == identifier if posting else E.id == identifier)
            .execution_options(populate_existing=True)
        )
        header = (await self._session.execute(statement)).one_or_none()
        if header is None:
            return None
        execution, posted, document, warehouse, status_change, return_details = header
        destination_location = aliased(L)
        line_statement = (
            select(
                EL, I, L, Nullable(Lot), Nullable(S), DL, Nullable(destination_location)
            )
            .join(I, I.id == EL.inventory_item_id)
            .join(L, L.id == EL.location_id)
            .outerjoin(
                destination_location,
                destination_location.id == EL.destination_location_id,
            )
            .outerjoin(Lot, Lot.id == EL.lot_id)
            .outerjoin(S, S.id == EL.serial_id)
            .join(DL, DL.id == EL.document_line_id)
            .where(EL.execution_id == execution.id)
            .order_by(EL.position, EL.id)
            .execution_options(populate_existing=True)
        )
        lines = (await self._session.execute(line_statement)).all()
        entries = (
            await self._session.scalars(
                select(Entry)
                .join(T, T.id == Entry.posting_id)
                .where(T.execution_id == execution.id)
                .order_by(Entry.position, Entry.id)
            )
        ).all()
        links = (
            await self._session.scalars(
                select(Link)
                .join(EL, EL.id == Link.execution_line_id)
                .where(EL.execution_id == execution.id)
                .order_by(Link.execution_line_id, Link.role)
            )
        ).all()
        costs = (
            await self._session.scalars(
                select(Cost).where(Cost.execution_id == execution.id).order_by(Cost.id)
            )
        ).all()
        allocations = (
            await self._session.scalars(
                select(Allocation)
                .join(Cost, Cost.id == Allocation.evidence_id)
                .where(Cost.execution_id == execution.id)
                .order_by(Allocation.evidence_id, Allocation.execution_line_id)
            )
        ).all()
        request = await self._session.scalar(
            select(Request).where(Request.execution_id == execution.id)
        )
        historical = (
            ReceiptPostingRecordMapper.to_execution(request.result)
            if request is not None and request.result is not None
            else None
        )
        return_lines = (
            await self._session.scalars(
                select(ReturnLine)
                .join(EL, EL.id == ReturnLine.execution_line_id)
                .where(EL.execution_id == execution.id)
            )
        ).all()
        return StockFactProjection(
            execution,
            posted,
            document,
            warehouse,
            tuple(
                (line, item, location, lot, serial, plan, destination)
                for line, item, location, lot, serial, plan, destination in lines
            ),
            entries,
            links,
            costs,
            allocations,
            historical,
            status_change,
            return_details,
            return_lines,
        )
