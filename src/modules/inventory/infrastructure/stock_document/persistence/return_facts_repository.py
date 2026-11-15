from src.modules.inventory.application.stock_document.query.list_return_destinations.query import (
    ListReturnDestinationsQuery,
)
from src.modules.inventory.application.stock_document.query.list_return_destinations.dto import (
    ListReturnDestinationsResultDTO,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_return_line import (
    StockDocumentReturnLineModel as ReturnLink,
)
from src.modules.inventory.infrastructure.stock_document.persistence.return_origin_query_repository import (
    SqlAlchemyReturnOriginQueryRepository,
)
from src.modules.inventory.application.stock_document.query.get_return_origin.query import (
    GetReturnOriginQuery,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document_return import (
    StockDocumentReturnModel as ReturnDetails,
)
from src.modules.inventory.application.stock_document.query.list_return_sources.query import (
    ListReturnSourcesQuery,
)
from src.modules.inventory.application.stock_document.query.list_return_sources.dto import (
    ListReturnSourcesResultDTO,
)
from src.modules.inventory.infrastructure.stock_document.persistence.return_progress_mapper import (
    ReturnProgressQueryMapper,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_lines import (
    StockExecutionLineModel as ActualLine,
)
from src.modules.inventory.application.stock_document.query.list_return_executions.dto import (
    ListReturnExecutionLineDTO,
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
from src.modules.inventory.application.stock_document.query.prepare_return.query import (
    PrepareReturnQuery,
)
from src.modules.inventory.application.stock_document.query.prepare_return.dto import (
    PrepareReturnResultDTO,
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
from src.modules.inventory.infrastructure.persistence.models.stock_return_posting_requests import (
    ReturnPostingRequestModel as Request,
)
from src.modules.inventory.infrastructure.persistence.models.stock_executions import (
    StockExecutionModel as Execution,
)
from src.modules.inventory.infrastructure.persistence.models.stock_document import (
    StockDocumentModel,
)
from src.modules.inventory.infrastructure.stock_document.persistence.return_record_mapper import (
    ReturnPostingRecordMapper,
)
from src.modules.inventory.application.stock_document.query.list_return_executions.query import (
    ListReturnExecutionsQuery,
)
from src.modules.inventory.application.stock_document.query.list_return_executions.dto import (
    ListReturnExecutionsResultDTO,
    ListReturnExecutionItemDTO,
)


class SqlAlchemyReturnFactsQueryRepository:
    """Читает подготовку возврата и неизменяемые факты без восстановления агрегатов."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает единственную tenant-сессию внешнего UoW."""
        self._session = session

    async def list_executions(
        self, query: ListReturnExecutionsQuery
    ) -> ListReturnExecutionsResultDTO | None:
        """Читает страницу и total с одним фильтром документа и стабильным порядком."""
        if (
            await self._session.scalar(
                select(StockDocumentModel.id).where(
                    StockDocumentModel.id == query.document_id,
                    StockDocumentModel.operation_type == "RETURN",
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
        progress: dict[UUID, list[ListReturnExecutionLineDTO]] = {}
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
                    ReturnProgressQueryMapper.to_history_line(
                        line, base_uom, quantity, count
                    )
                )
        items: list[ListReturnExecutionItemDTO] = []
        for execution, request in rows:
            if request.result is None:
                raise RuntimeError("Завершённый факт не содержит результата.")
            result = ReturnPostingRecordMapper.to_command(request.result)
            items.append(
                ListReturnExecutionItemDTO(
                    execution.id,
                    result.posting_id,
                    execution.executed_at,
                    result.document_version_after,
                    result.document_status,
                    result.reason,
                    result.direction,
                    result.origin_execution_id,
                    len(result.lines),
                    tuple(progress.get(execution.id, ())),
                )
            )
        return ListReturnExecutionsResultDTO(
            tuple(items), total, query.offset, query.limit
        )

    async def prepare(self, query: PrepareReturnQuery) -> PrepareReturnResultDTO | None:
        """Вычисляет точный оставшийся план в NUMERIC и дополняет актуальными настройками SKU."""
        statement = (
            select(
                StockDocumentModel,
                Warehouse,
                Nullable(PlanLine),
                Nullable(Item),
                Nullable(PlanLine.planned_qty - PlanLine.executed_qty),
                ReturnDetails,
            )
            .join(Warehouse, Warehouse.id == StockDocumentModel.warehouse_id)
            .join(ReturnDetails, ReturnDetails.document_id == StockDocumentModel.id)
            .outerjoin(PlanLine, PlanLine.document_id == StockDocumentModel.id)
            .outerjoin(Item, Item.id == PlanLine.inventory_item_id)
            .where(
                StockDocumentModel.id == query.document_id,
                StockDocumentModel.operation_type == "RETURN",
                StockDocumentModel.source_system.is_(None),
            )
            .order_by(PlanLine.position, PlanLine.id)
            .execution_options(populate_existing=True)
        )
        rows = (await self._session.execute(statement)).all()
        if not rows:
            return None
        document, warehouse = rows[0][0], rows[0][1]
        links = (
            await self._session.execute(
                select(PlanLine.id, ReturnLink.origin_execution_line_id)
                .join(ReturnLink, ReturnLink.document_line_id == PlanLine.id)
                .where(PlanLine.document_id == document.id)
            )
        ).all()
        origin_id = rows[0][5].origin_execution_id
        origin_page = await SqlAlchemyReturnOriginQueryRepository(self._session).get(
            GetReturnOriginQuery(origin_id), direction=rows[0][5].direction
        )
        if origin_page is None:
            raise RuntimeError("Отсутствует исходный факт.")
        by_origin = {v.id: v for v in origin_page.lines}
        by_plan = dict(links)
        return PrepareReturnResultDTO(
            document.id,
            document.version,
            document.status,
            document.warehouse_id,
            rows[0][5].reason,
            rows[0][5].direction,
            origin_id,
            tuple(
                ReturnProgressQueryMapper.to_preparation_line(
                    line,
                    item,
                    remaining,
                    origin_line_id=by_plan[line.id],
                    original_quantity=by_origin[by_plan[line.id]].quantity,
                    returned_quantity=by_origin[by_plan[line.id]].returned_quantity,
                    returnable_quantity=by_origin[by_plan[line.id]].remaining_quantity,
                )
                for _, _, line, item, remaining, _ in rows
                if line is not None and item is not None and remaining is not None
            ),
        )

    async def sources(
        self, query: ListReturnSourcesQuery
    ) -> ListReturnSourcesResultDTO | None:
        """Ищет физические позиции той же строки, склада и владельца без условий резервов или FEFO."""
        statement_scope = (
            select(
                StockDocumentModel.warehouse_id,
                StockDocumentModel.owner_id,
                PlanLine.inventory_item_id,
                ReturnDetails.origin_execution_id,
                ReturnLink.origin_execution_line_id,
            )
            .join(PlanLine, PlanLine.document_id == StockDocumentModel.id)
            .join(ReturnLink, ReturnLink.document_line_id == PlanLine.id)
            .join(ReturnDetails, ReturnDetails.document_id == StockDocumentModel.id)
            .where(
                StockDocumentModel.id == query.document_id,
                StockDocumentModel.operation_type == "RETURN",
                StockDocumentModel.source_system.is_(None),
                PlanLine.id == query.document_line_id,
            )
        )
        scope = (await self._session.execute(statement_scope)).one_or_none()
        if scope is None:
            return None
        warehouse_id, owner_id, item_id, origin_id, origin_line_id = scope
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
        origin_line = (
            await self._session.scalars(
                select(ActualLine).where(
                    ActualLine.id == origin_line_id,
                    ActualLine.execution_id == origin_id,
                )
            )
        ).one()
        filters += (
            Position.lot_id.is_not_distinct_from(origin_line.lot_id),
            Position.serial_id.is_not_distinct_from(origin_line.serial_id),
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
        return ListReturnSourcesResultDTO(
            tuple(
                ReturnProgressQueryMapper.to_source(position, location, lot, serial)
                for position, location, lot, serial in rows
            ),
            total,
            query.offset,
            query.limit,
        )

    async def destinations(
        self, query: ListReturnDestinationsQuery
    ) -> ListReturnDestinationsResultDTO | None:
        """Читает активные адреса склада с общими фильтрами страницы и total."""
        warehouse_id = await self._session.scalar(
            select(StockDocumentModel.warehouse_id).where(
                StockDocumentModel.id == query.document_id,
                StockDocumentModel.operation_type == "RETURN",
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
        return ListReturnDestinationsResultDTO(
            tuple(ReturnProgressQueryMapper.to_destination(row) for row in rows),
            total,
            query.offset,
            query.limit,
        )
