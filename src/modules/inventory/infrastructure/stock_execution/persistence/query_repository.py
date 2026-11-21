from sqlalchemy import select, func, Nullable
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.infrastructure.persistence.models.warehouse import (
    WarehouseModel as W,
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
from src.modules.inventory.infrastructure.persistence.models.stock_document import (
    StockDocumentModel as D,
)
from src.modules.inventory.infrastructure.accounting.persistence.filters import (
    fact_filters,
)
from src.modules.inventory.infrastructure.accounting.persistence.fact_projection import (
    StockFactProjectionReader,
)
from src.modules.inventory.infrastructure.stock_execution.persistence.query_mapper import (
    StockExecutionQueryMapper,
)
from src.modules.inventory.application.stock_execution.query.list_stock_executions.query import (
    ListStockExecutionsQuery,
)
from src.modules.inventory.application.stock_execution.query.list_stock_executions.dto import (
    ListStockExecutionsResultDTO,
)
from src.modules.inventory.application.stock_execution.query.get_stock_execution_details.query import (
    GetStockExecutionDetailsQuery,
)
from src.modules.inventory.application.stock_execution.query.get_stock_execution_details.dto import (
    GetStockExecutionDetailsResultDTO,
)


class SqlAlchemyStockExecutionQueryRepository:
    """Читает общие списки и нормализованные карточки физического учёта."""

    def __init__(self, session: AsyncSession) -> None:
        """Принимает единственную tenant-сессию внешнего UoW."""
        self._session = session

    async def details(
        self, query: GetStockExecutionDetailsQuery
    ) -> GetStockExecutionDetailsResultDTO | None:
        """Читает факт независимо от наличия ключа команды приёмки."""
        value = await StockFactProjectionReader(self._session).read(
            query.identifier, posting=False
        )
        return StockExecutionQueryMapper.details(value) if value else None

    async def list(
        self, query: ListStockExecutionsQuery
    ) -> ListStockExecutionsResultDTO:
        """Применяет один EXISTS-фильтр для подходящей строки без дублирования факта."""
        filters = fact_filters(query.filters)
        count_statement = (
            select(func.count())
            .select_from(E)
            .outerjoin(T, T.execution_id == E.id)
            .where(*filters)
        )
        total = (await self._session.execute(count_statement)).scalar_one()
        line_count = (
            select(func.count())
            .select_from(EL)
            .where(EL.execution_id == E.id)
            .correlate(E)
            .scalar_subquery()
        )
        statement = (
            select(E, Nullable(T), D, W, line_count)
            .outerjoin(T, T.execution_id == E.id)
            .join(D, D.id == E.document_id)
            .join(W, W.id == E.warehouse_id)
            .where(*filters)
            .order_by(E.executed_at.desc(), E.id.desc())
            .offset(query.offset)
            .limit(query.limit)
        )
        rows = (await self._session.execute(statement)).all()
        return ListStockExecutionsResultDTO(
            tuple(
                StockExecutionQueryMapper.to_list_item(e, t, d, w, count)
                for e, t, d, w, count in rows
            ),
            total,
            query.offset,
            query.limit,
        )
