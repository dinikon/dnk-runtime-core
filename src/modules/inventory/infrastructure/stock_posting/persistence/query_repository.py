from src.modules.inventory.infrastructure.persistence.models.stock_execution_return import (
    StockExecutionReturnModel as ReturnDetails,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_status_change import (
    StockExecutionStatusChangeModel as StatusDetails,
)
from src.modules.inventory.application.stock_posting.query.list_stock_movements.query import (
    ListStockMovementsQuery,
)
from src.modules.inventory.application.stock_posting.query.list_stock_movements.dto import (
    ListStockMovementsResultDTO,
    MovementPositionSnapshotDTO,
)
from src.modules.inventory.infrastructure.accounting.persistence.query_mapper import (
    StockAccountingQueryMapper as Mapper,
)
from src.modules.inventory.domain.stock_document.receipt_error import (
    ReceiptFactNotFoundError,
)
from src.modules.inventory.domain.stock_position.error import (
    StockPositionVersionConflictError,
)
from sqlalchemy import select, func, Nullable
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.infrastructure.persistence.models.stock_positions import (
    StockPositionModel as P,
)
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
from src.modules.inventory.infrastructure.accounting.persistence.filters import (
    fact_filters,
    dimension_filters,
)
from src.modules.inventory.infrastructure.accounting.persistence.fact_projection import (
    StockFactProjectionReader,
)
from src.modules.inventory.infrastructure.stock_posting.persistence.query_mapper import (
    StockPostingQueryMapper,
)
from src.modules.inventory.application.stock_posting.query.list_stock_postings.query import (
    ListStockPostingsQuery,
)
from src.modules.inventory.application.stock_posting.query.list_stock_postings.dto import (
    ListStockPostingsResultDTO,
)
from src.modules.inventory.application.stock_posting.query.get_stock_posting_details.query import (
    GetStockPostingDetailsQuery,
)
from src.modules.inventory.application.stock_posting.query.get_stock_posting_details.dto import (
    GetStockPostingDetailsResultDTO,
)


class SqlAlchemyStockPostingQueryRepository:
    """Читает общие списки и нормализованные карточки физического учёта."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает единственную tenant-сессию внешнего UoW."""
        self._session = session

    async def details(
        self, query: GetStockPostingDetailsQuery
    ) -> GetStockPostingDetailsResultDTO | None:
        """Читает факт независимо от наличия ключа команды приёмки."""
        value = await StockFactProjectionReader(self._session).read(
            query.identifier, posting=True
        )
        return StockPostingQueryMapper.details(value) if value else None

    async def list(self, query: ListStockPostingsQuery) -> ListStockPostingsResultDTO:
        """Применяет один EXISTS-фильтр для подходящей строки без дублирования факта."""
        filters = fact_filters(query.filters)
        total = (
            await self._session.execute(
                select(func.count())
                .select_from(T)
                .join(E, E.id == T.execution_id)
                .where(*filters)
            )
        ).scalar_one()
        entry_count = (
            select(func.count())
            .select_from(Entry)
            .where(Entry.posting_id == T.id)
            .correlate(T)
            .scalar_subquery()
        )
        statement = (
            select(T, E, D, W, entry_count)
            .join(E, E.id == T.execution_id)
            .join(D, D.id == E.document_id)
            .join(W, W.id == E.warehouse_id)
            .where(*filters)
            .order_by(T.posted_at.desc(), T.id.desc())
            .offset(query.offset)
            .limit(query.limit)
        )
        rows = (await self._session.execute(statement)).all()
        return ListStockPostingsResultDTO(
            tuple(
                StockPostingQueryMapper.to_list_item(t, e, d, w, count)
                for t, e, d, w, count in rows
            ),
            total,
            query.offset,
            query.limit,
        )

    async def movements(
        self, query: ListStockMovementsQuery
    ) -> ListStockMovementsResultDTO:
        """Сверяет версию позиции до и после составного чтения, не блокируя проведение."""
        for _ in range(3):
            position = (
                await self._session.scalar(
                    select(P)
                    .where(P.id == query.filters.position_id)
                    .execution_options(populate_existing=True)
                )
                if query.filters.position_id
                else None
            )
            if query.filters.position_id and position is None:
                raise ReceiptFactNotFoundError("Физическая позиция не найдена.")
            snapshot = (
                MovementPositionSnapshotDTO(
                    position.id, position.on_hand_qty, position.version
                )
                if position
                else None
            )
            result = await self._read_movements(query, snapshot)
            if snapshot is None:
                return result
            version = await self._session.scalar(
                select(P.version).where(P.id == snapshot.id)
            )
            if version == snapshot.version:
                return result
        raise StockPositionVersionConflictError(
            "Остаток изменяется. Обновите журнал движений."
        )

    async def _read_movements(
        self,
        query: ListStockMovementsQuery,
        snapshot: MovementPositionSnapshotDTO | None,
    ) -> ListStockMovementsResultDTO:
        """Читает одну строку на Ledger; детализацию связей загружает одним пакетным запросом."""
        filters = dimension_filters(query.filters)
        for field, value in (
            (D.id, query.filters.document_id),
            (E.id, query.filters.execution_id),
            (T.id, query.filters.posting_id),
            (T.operation_type, query.filters.operation_type),
        ):
            if value is not None:
                filters += (field == value,)
        if query.filters.posted_from:
            filters += (T.posted_at >= query.filters.posted_from,)
        if query.filters.posted_to:
            filters += (T.posted_at < query.filters.posted_to,)
        count_statement = (
            select(func.count())
            .select_from(Entry)
            .join(P, P.id == Entry.position_id)
            .join(L, L.id == P.location_id)
            .join(I, I.id == P.inventory_item_id)
            .outerjoin(Lot, Lot.id == P.lot_id)
            .outerjoin(S, S.id == P.serial_id)
            .join(T, T.id == Entry.posting_id)
            .join(E, E.id == T.execution_id)
            .join(D, D.id == E.document_id)
            .where(*filters)
        )
        total = (await self._session.execute(count_statement)).scalar_one()
        statement = (
            select(
                P,
                L,
                W,
                I,
                Nullable(Lot),
                Nullable(S),
                Entry,
                T,
                E,
                D,
                Nullable(StatusDetails),
                Nullable(ReturnDetails),
            )
            .select_from(Entry)
            .join(P, P.id == Entry.position_id)
            .join(L, L.id == P.location_id)
            .join(W, W.id == L.warehouse_id)
            .join(I, I.id == P.inventory_item_id)
            .outerjoin(Lot, Lot.id == P.lot_id)
            .outerjoin(S, S.id == P.serial_id)
            .join(T, T.id == Entry.posting_id)
            .join(E, E.id == T.execution_id)
            .join(D, D.id == E.document_id)
            .outerjoin(StatusDetails, StatusDetails.execution_id == E.id)
            .outerjoin(ReturnDetails, ReturnDetails.execution_id == E.id)
            .where(*filters)
            .order_by(T.posted_at.desc(), T.id.desc(), Entry.position, Entry.id)
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(statement)).all()
        ids = tuple(row[6].id for row in rows)
        links = (
            (
                await self._session.execute(
                    select(Link, DL.sku)
                    .join(EL, EL.id == Link.execution_line_id)
                    .join(DL, DL.id == EL.document_line_id)
                    .where(Link.ledger_entry_id.in_(ids))
                    .order_by(Link.execution_line_id, Link.role)
                )
            ).all()
            if ids
            else ()
        )
        items = tuple(
            Mapper.movement(
                p,
                l,
                w,
                item,
                lot,
                serial,
                entry,
                posted,
                execution,
                document,
                tuple(
                    dict.fromkeys(
                        link.execution_line_id
                        for link, _ in links
                        if link.ledger_entry_id == entry.id
                    )
                ),
                tuple(
                    dict.fromkeys(
                        sku for link, sku in links if link.ledger_entry_id == entry.id
                    )
                ),
                status_change,
                return_details,
            )
            for p, l, w, item, lot, serial, entry, posted, execution, document, status_change, return_details in rows
        )
        return ListStockMovementsResultDTO(
            items, total, query.offset, query.limit, snapshot
        )
