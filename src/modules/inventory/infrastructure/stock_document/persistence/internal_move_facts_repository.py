from src.modules.inventory.application.stock_document.query.list_internal_move_destinations.query import (
    ListInternalMoveDestinationsQuery,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_destinations.dto import (
    ListInternalMoveDestinationsResultDTO,
    InternalMoveDestinationDTO,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_sources.query import (
    ListInternalMoveSourcesQuery,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_sources.dto import (
    ListInternalMoveSourcesResultDTO,
)
from src.modules.inventory.infrastructure.stock_document.persistence.internal_move_progress_mapper import (
    InternalMoveProgressQueryMapper,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_lines import (
    StockExecutionLineModel as ActualLine,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_executions.dto import (
    ListInternalMoveExecutionLineDTO,
)
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
from src.modules.inventory.application.stock_document.query.prepare_internal_move.query import (
    PrepareInternalMoveQuery,
)
from src.modules.inventory.application.stock_document.query.prepare_internal_move.dto import (
    PrepareInternalMoveResultDTO,
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
from src.modules.inventory.infrastructure.persistence.models.stock_internal_move_posting_requests import (
    InternalMovePostingRequestModel as Request,
)
from src.modules.inventory.infrastructure.persistence.models.stock_executions import (
    StockExecutionModel as Execution,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document import (
    StockDocumentModel,
)
from src.modules.inventory.infrastructure.stock_document.persistence.internal_move_record_mapper import (
    InternalMovePostingRecordMapper,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_executions.query import (
    ListInternalMoveExecutionsQuery,
)
from src.modules.inventory.application.stock_document.query.list_internal_move_executions.dto import (
    ListInternalMoveExecutionsResultDTO,
    ListInternalMoveExecutionItemDTO,
)


class SqlAlchemyInternalMoveFactsQueryRepository:
    """Читает подготовку перемещения и неизменяемые факты без восстановления агрегатов."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает единственную tenant-сессию внешнего UoW."""
        self._session = session

    async def list_executions(
        self, query: ListInternalMoveExecutionsQuery
    ) -> ListInternalMoveExecutionsResultDTO | None:
        """Читает страницу и total с одним фильтром документа и стабильным порядком."""
        if (
            await self._session.scalar(
                select(StockDocumentModel.id).where(
                    StockDocumentModel.id == query.document_id,
                    StockDocumentModel.operation_type == "INTERNAL_MOVE",
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
        progress: dict[UUID, list[ListInternalMoveExecutionLineDTO]] = {}
        if rows:
            statement_lines = (
                select(
                    ActualLine.execution_id,
                    PlanLine,
                    ActualLine.base_uom,
                    func.sum(ActualLine.quantity),
                    func.count(ActualLine.id),
                )
                .join(PlanLine, PlanLine.id == ActualLine.document_line_id)
                .where(
                    ActualLine.execution_id.in_([execution.id for execution, _ in rows])
                )
                .group_by(ActualLine.execution_id, PlanLine.id, ActualLine.base_uom)
                .order_by(ActualLine.execution_id, PlanLine.position, PlanLine.id)
                .execution_options(populate_existing=True)
            )
            line_rows = (await self._session.execute(statement_lines)).all()
            for execution_id, line, base_uom, quantity, count in line_rows:
                progress.setdefault(execution_id, []).append(
                    InternalMoveProgressQueryMapper.to_history_line(
                        line, base_uom, quantity, count
                    )
                )
        items: list[ListInternalMoveExecutionItemDTO] = []
        for execution, request in rows:
            if request.result is None:
                raise RuntimeError("Завершённый факт не содержит результата.")
            result = InternalMovePostingRecordMapper.to_command(request.result)
            items.append(
                ListInternalMoveExecutionItemDTO(
                    execution.id,
                    result.posting_id,
                    execution.executed_at,
                    result.document_version_after,
                    result.document_status,
                    len(result.lines),
                    tuple(progress.get(execution.id, ())),
                )
            )
        return ListInternalMoveExecutionsResultDTO(
            tuple(items), total, query.offset, query.limit
        )

    async def prepare(
        self, query: PrepareInternalMoveQuery
    ) -> PrepareInternalMoveResultDTO | None:
        """Вычисляет точный оставшийся план в NUMERIC и дополняет актуальными настройками SKU."""
        statement = (
            select(
                StockDocumentModel,
                Warehouse,
                Nullable(PlanLine),
                Nullable(Item),
                Nullable(PlanLine.planned_qty - PlanLine.executed_qty),
            )
            .join(Warehouse, Warehouse.id == StockDocumentModel.warehouse_id)
            .outerjoin(PlanLine, PlanLine.document_id == StockDocumentModel.id)
            .outerjoin(Item, Item.id == PlanLine.inventory_item_id)
            .where(
                StockDocumentModel.id == query.document_id,
                StockDocumentModel.operation_type == "INTERNAL_MOVE",
                StockDocumentModel.source_system.is_(None),
            )
            .order_by(PlanLine.position, PlanLine.id)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(statement)).all()
        if not rows:
            return None
        document, warehouse = rows[0][0], rows[0][1]
        return PrepareInternalMoveResultDTO(
            document.id,
            document.version,
            document.status,
            document.warehouse_id,
            tuple(
                InternalMoveProgressQueryMapper.to_preparation_line(
                    line, item, remaining
                )
                for _, _, line, item, remaining in rows
                if line is not None and item is not None and remaining is not None
            ),
        )

    async def sources(
        self, query: ListInternalMoveSourcesQuery
    ) -> ListInternalMoveSourcesResultDTO | None:
        """Ищет физические позиции той же строки, склада и владельца без условий резервов или FEFO."""
        statement_scope = (
            select(
                StockDocumentModel.warehouse_id,
                StockDocumentModel.owner_id,
                PlanLine.inventory_item_id,
            )
            .join(PlanLine, PlanLine.document_id == StockDocumentModel.id)
            .where(
                StockDocumentModel.id == query.document_id,
                StockDocumentModel.operation_type == "INTERNAL_MOVE",
                StockDocumentModel.source_system.is_(None),
                PlanLine.id == query.document_line_id,
            )
        )
        scope = (await self._session.execute(statement_scope)).one_or_none()
        if scope is None:
            return None
        warehouse_id, owner_id, item_id = scope
        filters: tuple[ColumnElement[bool], ...] = (
            Position.inventory_item_id == item_id,
            Position.owner_id == owner_id,
            Location.warehouse_id == warehouse_id,
            Location.is_active.is_(True),
        )
        filters += (
            (Position.id == query.position_id,)
            if query.position_id is not None
            else (Position.on_hand_qty > 0,)
        )
        if query.search:
            filters += (
                or_(
                    Location.code.icontains(query.search, autoescape=True),
                    Location.name.icontains(query.search, autoescape=True),
                    Lot.number.icontains(query.search, autoescape=True),
                    Serial.number.icontains(query.search, autoescape=True),
                ),
            )
        count_statement = (
            select(func.count())
            .select_from(Position)
            .join(Location, Location.id == Position.location_id)
            .outerjoin(Lot, Lot.id == Position.lot_id)
            .outerjoin(Serial, Serial.id == Position.serial_id)
            .where(*filters)
        )
        total = (await self._session.execute(count_statement)).scalar_one()
        statement = (
            select(Position, Location, Nullable(Lot), Nullable(Serial))
            .join(Location, Location.id == Position.location_id)
            .outerjoin(Lot, Lot.id == Position.lot_id)
            .outerjoin(Serial, Serial.id == Position.serial_id)
            .where(*filters)
            .order_by(Location.code, Position.id)
            .offset(query.offset)
            .limit(query.limit)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(statement)).all()
        return ListInternalMoveSourcesResultDTO(
            tuple(
                InternalMoveProgressQueryMapper.to_source(
                    position, location, lot, serial
                )
                for position, location, lot, serial in rows
            ),
            total,
            query.offset,
            query.limit,
        )

    async def destinations(
        self, query: ListInternalMoveDestinationsQuery
    ) -> ListInternalMoveDestinationsResultDTO | None:
        """Читает активные адреса склада с общими фильтрами страницы и total."""
        warehouse_id = await self._session.scalar(
            select(StockDocumentModel.warehouse_id).where(
                StockDocumentModel.id == query.document_id,
                StockDocumentModel.operation_type == "INTERNAL_MOVE",
                StockDocumentModel.source_system.is_(None),
            )
        )
        if warehouse_id is None:
            return None
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
        if query.location_id:
            filters += (Location.id == query.location_id,)
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
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.scalars(statement)).all()
        return ListInternalMoveDestinationsResultDTO(
            tuple(InternalMoveProgressQueryMapper.to_destination(row) for row in rows),
            total,
            query.offset,
            query.limit,
        )
