from sqlalchemy import Nullable, or_
from sqlalchemy.sql.elements import ColumnElement
from src.modules.inventory.infrastructure.persistence.models.stock_location import (
    StockLocationModel as Location,
)
from src.modules.inventory.infrastructure.persistence.models.stock_lot import (
    StockLotModel as Lot,
)
from src.modules.inventory.infrastructure.persistence.models.stock_serial import (
    StockSerialModel as Serial,
)
from src.modules.inventory.infrastructure.persistence.models.stock_positions import (
    StockPositionModel as Position,
)
from src.modules.inventory.application.stock_document.query.list_receipt_references.query import (
    ListReceiptReferencesQuery,
)
from src.modules.inventory.application.stock_document.query.list_receipt_references.dto import (
    ListReceiptReferencesResultDTO,
    ReceiptReferenceItemDTO,
)
from src.modules.inventory.application.stock_document.query.prepare_receipt.query import (
    PrepareReceiptQuery,
)
from src.modules.inventory.application.stock_document.query.prepare_receipt.dto import (
    PrepareReceiptResultDTO,
    PrepareReceiptLineDTO,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_line import (
    StockDocumentLineModel as PlanLine,
)
from src.modules.inventory.infrastructure.persistence.models.inventory_item import (
    InventoryItemModel as Item,
)
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel as Warehouse,
)
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.infrastructure.persistence.models.stock_receipt_posting_requests import (
    ReceiptPostingRequestModel as Request,
)
from src.modules.inventory.infrastructure.persistence.models.stock_executions import (
    StockExecutionModel as Execution,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document import (
    StockDocumentModel,
)
from src.modules.inventory.infrastructure.stock_document.persistence.receipt_record_mapper import (
    ReceiptPostingRecordMapper,
)
from src.modules.inventory.application.stock_execution.query.get_stock_execution.dto import (
    GetStockExecutionResultDTO,
)
from src.modules.inventory.application.stock_posting.query.get_stock_posting.dto import (
    GetStockPostingResultDTO,
)
from src.modules.inventory.application.stock_document.query.list_receipt_executions.query import (
    ListReceiptExecutionsQuery,
)
from src.modules.inventory.application.stock_document.query.list_receipt_executions.dto import (
    ListReceiptExecutionsResultDTO,
    ListReceiptExecutionItemDTO,
)


class SqlAlchemyReceiptFactsQueryRepository:
    """Читает неизменяемые проекции первоначального результата без Domain и текущих остатков."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает единственную tenant-сессию внешнего UoW."""
        self._session = session

    async def get_execution(
        self, identifier: UUID
    ) -> GetStockExecutionResultDTO | None:
        """Читает конкретную карточку исполнения, включая исторические дельты и основания."""
        statement = (
            select(Request)
            .where(Request.execution_id == identifier)
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        if model is None:
            return None
        if model.result is None:
            raise RuntimeError("Завершённый факт не содержит результата.")
        return ReceiptPostingRecordMapper.to_execution(model.result)

    async def get_posting(self, identifier: UUID) -> GetStockPostingResultDTO | None:
        """Читает карточку проводки с неизменяемым Ledger."""
        statement = (
            select(Request)
            .where(Request.posting_id == identifier)
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        if model is None:
            return None
        if model.result is None:
            raise RuntimeError("Завершённый факт не содержит результата.")
        return ReceiptPostingRecordMapper.to_posting(model.result)

    async def list_executions(
        self, query: ListReceiptExecutionsQuery
    ) -> ListReceiptExecutionsResultDTO | None:
        """Читает страницу и total с одним фильтром документа и стабильным порядком."""
        if (
            await self._session.scalar(
                select(StockDocumentModel.id).where(
                    StockDocumentModel.id == query.document_id,
                    StockDocumentModel.operation_type == "RECEIPT",
                )
            )
            is None
        ):
            return None
        filters: tuple[ColumnElement[bool], ...] = (
            Execution.document_id == query.document_id,
        )
        total = (
            await self._session.execute(
                select(func.count()).select_from(Execution).where(*filters)
            )
        ).scalar_one()
        statement = (
            select(Execution, Request)
            .join(Request, Request.execution_id == Execution.id)
            .where(*filters)
            .order_by(Execution.executed_at.desc(), Execution.id.desc())
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(statement)).all()
        items = []
        for execution, request in rows:
            if request.result is None:
                raise RuntimeError("Завершённый факт не содержит результата.")
            result = ReceiptPostingRecordMapper.to_execution(request.result)
            items.append(
                ListReceiptExecutionItemDTO(
                    execution.id,
                    result.posting_id,
                    execution.executed_at,
                    result.document_version_after,
                    result.document_status,
                    len(result.lines),
                )
            )
        return ListReceiptExecutionsResultDTO(
            tuple(items), total, query.offset, query.limit
        )

    async def prepare(
        self, query: PrepareReceiptQuery
    ) -> PrepareReceiptResultDTO | None:
        """Вычисляет точный оставшийся план в NUMERIC и дополняет актуальными настройками SKU."""
        statement = (
            select(StockDocumentModel, Warehouse)
            .join(Warehouse, Warehouse.id == StockDocumentModel.warehouse_id)
            .where(
                StockDocumentModel.id == query.document_id,
                StockDocumentModel.operation_type == "RECEIPT",
                StockDocumentModel.source_system.is_(None),
            )
            .execution_options(populate_existing=True)
        )
        header = (await self._session.execute(statement)).one_or_none()
        if header is None:
            return None
        document, warehouse = header
        statement_lines = (
            select(
                PlanLine,
                Item,
                (PlanLine.planned_qty - PlanLine.executed_qty).label("remaining"),
            )
            .join(Item, Item.id == PlanLine.inventory_item_id)
            .where(PlanLine.document_id == document.id)
            .order_by(PlanLine.position, PlanLine.id)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(statement_lines)).all()
        return PrepareReceiptResultDTO(
            document.id,
            document.version,
            document.status,
            document.warehouse_id,
            warehouse.default_storage_location_id,
            tuple(
                PrepareReceiptLineDTO(
                    line.id,
                    item.id,
                    line.sku,
                    line.base_uom,
                    item.base_uom,
                    remaining,
                    item.quantity_step,
                    item.tracking_mode,
                    item.expiration_mode,
                )
                for line, item, remaining in rows
            ),
        )

    async def references(
        self, query: ListReceiptReferencesQuery
    ) -> ListReceiptReferencesResultDTO | None:
        """Ищет только в складе документа или SKU его строки, исключая положительное присутствие SERIAL."""
        warehouse_id = await self._session.scalar(
            select(StockDocumentModel.warehouse_id).where(
                StockDocumentModel.id == query.document_id,
                StockDocumentModel.operation_type == "RECEIPT",
                StockDocumentModel.source_system.is_(None),
            )
        )
        if warehouse_id is None:
            return None
        if query.kind == "locations":
            filters: tuple[ColumnElement[bool], ...] = (
                Location.warehouse_id == warehouse_id,
                Location.is_active.is_(True),
            )
            if query.search:
                filters += (
                    or_(
                        Location.code.icontains(query.search, autoescape=True),
                        Location.name.icontains(query.search, autoescape=True),
                    ),
                )
            total = (
                await self._session.execute(
                    select(func.count()).select_from(Location).where(*filters)
                )
            ).scalar_one()
            statement = (
                select(Location)
                .where(*filters)
                .order_by(Location.code, Location.id)
                .offset(query.offset)
                .limit(query.limit)
            )
            rows = (await self._session.scalars(statement)).all()
            return ListReceiptReferencesResultDTO(
                tuple(
                    ReceiptReferenceItemDTO(row.id, f"{row.code} — {row.name}")
                    for row in rows
                ),
                total,
                query.offset,
                query.limit,
            )
        item_id = await self._session.scalar(
            select(PlanLine.inventory_item_id).where(
                PlanLine.id == query.document_line_id,
                PlanLine.document_id == query.document_id,
            )
        )
        if item_id is None:
            return None
        if query.kind == "lots":
            lot_filters: tuple[ColumnElement[bool], ...] = (
                Lot.inventory_item_id == item_id,
            )
            if query.search:
                lot_filters += (Lot.number.icontains(query.search, autoescape=True),)
            total = (
                await self._session.execute(
                    select(func.count()).select_from(Lot).where(*lot_filters)
                )
            ).scalar_one()
            statement_lots = (
                select(Lot)
                .where(*lot_filters)
                .order_by(Lot.number, Lot.id)
                .offset(query.offset)
                .limit(query.limit)
            )
            lot_rows = (await self._session.scalars(statement_lots)).all()
            return ListReceiptReferencesResultDTO(
                tuple(
                    ReceiptReferenceItemDTO(
                        row.id,
                        row.number,
                        row.id,
                        row.number,
                        row.manufactured_on,
                        row.expires_on,
                    )
                    for row in lot_rows
                ),
                total,
                query.offset,
                query.limit,
            )
        serial_filters: tuple[ColumnElement[bool], ...] = (
            Serial.inventory_item_id == item_id,
            ~select(Position.id)
            .where(Position.serial_id == Serial.id, Position.on_hand_qty > 0)
            .exists(),
        )
        if query.search:
            serial_filters += (Serial.number.icontains(query.search, autoescape=True),)
        if query.lot_id is not None:
            serial_filters += (Serial.lot_id == query.lot_id,)
        total = (
            await self._session.execute(
                select(func.count()).select_from(Serial).where(*serial_filters)
            )
        ).scalar_one()
        statement_serials = (
            select(Serial, Nullable(Lot))
            .outerjoin(Lot, Lot.id == Serial.lot_id)
            .where(*serial_filters)
            .order_by(Serial.number, Serial.id)
            .offset(query.offset)
            .limit(query.limit)
        )
        serial_rows = (await self._session.execute(statement_serials)).all()
        return ListReceiptReferencesResultDTO(
            tuple(
                ReceiptReferenceItemDTO(
                    row.id,
                    row.number,
                    row.lot_id,
                    lot.number if lot else None,
                    lot.manufactured_on if lot else None,
                    lot.expires_on if lot else None,
                )
                for row, lot in serial_rows
            ),
            total,
            query.offset,
            query.limit,
        )
