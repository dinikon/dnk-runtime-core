from src.modules.inventory.infrastructure.persistence.models.stock_execution_return import (
    StockExecutionReturnModel as ReturnDetails,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_return_line import (
    StockExecutionReturnLineModel as ReturnLine,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_status_change import (
    StockExecutionStatusChangeModel as StatusDetails,
)
from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.domain.stock_execution.aggregate import StockExecution
from src.modules.inventory.domain.stock_execution.value_object.identifier import (
    StockExecutionIdVO,
)
from src.modules.inventory.infrastructure.stock_execution.persistence.mapper import (
    StockExecutionMapper,
)
from src.modules.inventory.infrastructure.persistence.models.stock_executions import (
    StockExecutionModel as Header,
)
from src.modules.inventory.infrastructure.persistence.models.stock_execution_lines import (
    StockExecutionLineModel as Line,
)
from src.modules.inventory.infrastructure.persistence.models.stock_receipt_cost_evidence import (
    ReceiptCostEvidenceModel as Cost,
)
from src.modules.inventory.infrastructure.persistence.models.stock_receipt_cost_allocations import (
    ReceiptCostAllocationModel as Allocation,
)


class SqlAlchemyStockExecutionRepository:
    """Добавляет полный неизменяемый факт без методов изменения и удаления."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию единственного внешнего UoW."""
        self._session = session

    async def add(self, execution: StockExecution) -> None:
        """Вставляет корень, строки и исходные стоимостные сведения одной транзакцией."""
        await self._session.execute(
            insert(Header).values(StockExecutionMapper.to_values(execution))
        )
        if execution.status_change_details is not None:
            await self._session.execute(
                insert(StatusDetails).values(
                    StockExecutionMapper.status_change_values(execution)
                )
            )
        await self._session.execute(
            insert(Line), StockExecutionMapper.line_values(execution)
        )
        if execution.return_details is not None:
            await self._session.execute(
                insert(ReturnDetails).values(
                    StockExecutionMapper.return_values(execution)
                )
            )
            links = StockExecutionMapper.return_line_values(execution)
            if links:
                await self._session.execute(insert(ReturnLine), links)
        costs = StockExecutionMapper.cost_values(execution)
        if costs:
            await self._session.execute(insert(Cost), costs)
        allocations = StockExecutionMapper.allocation_values(execution)
        if allocations:
            await self._session.execute(insert(Allocation), allocations)

    async def get(self, identifier: StockExecutionIdVO) -> StockExecution | None:
        """Восстанавливает все принадлежащие факту данные с сохранёнными ID."""
        statement = (
            select(Header)
            .where(Header.id == identifier.uuid)
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        if model is None:
            return None
        lines = (
            await self._session.scalars(
                select(Line)
                .where(Line.execution_id == model.id)
                .order_by(Line.position)
                .execution_options(populate_existing=True)
            )
        ).all()
        costs = (
            await self._session.scalars(
                select(Cost)
                .where(Cost.execution_id == model.id)
                .order_by(Cost.id)
                .execution_options(populate_existing=True)
            )
        ).all()
        allocations = (
            await self._session.scalars(
                select(Allocation)
                .join(Cost, Allocation.evidence_id == Cost.id)
                .where(Cost.execution_id == model.id)
                .execution_options(populate_existing=True)
            )
        ).all()
        details = (
            await self._session.scalars(
                select(StatusDetails)
                .where(StatusDetails.execution_id == model.id)
                .execution_options(populate_existing=True)
            )
        ).one_or_none()
        return_details = (
            await self._session.scalars(
                select(ReturnDetails).where(ReturnDetails.execution_id == model.id)
            )
        ).one_or_none()
        return_lines = (
            await self._session.scalars(
                select(ReturnLine)
                .join(Line, Line.id == ReturnLine.execution_line_id)
                .where(Line.execution_id == model.id)
            )
        ).all()
        return StockExecutionMapper.to_domain(
            model, lines, costs, allocations, details, return_details, return_lines
        )
