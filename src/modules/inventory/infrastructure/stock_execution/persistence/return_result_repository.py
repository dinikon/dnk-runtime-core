from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.inventory.infrastructure.persistence.models.stock_return_posting_requests import (
    ReturnPostingRequestModel,
)
from src.modules.inventory.application.stock_execution.query.get_return_execution_result.query import (
    GetReturnExecutionResultQuery,
)
from src.modules.inventory.application.stock_execution.query.get_return_execution_result.dto import (
    GetReturnExecutionResultDTO,
)


class SqlAlchemyReturnExecutionResultRepository:
    """Читает immutable JSON результата, не восстанавливая доменные агрегаты."""

    def __init__(self, session: AsyncSession) -> None:
        """Получает сессию внешнего tenant-UoW."""
        self._session = session

    async def get(
        self, query: GetReturnExecutionResultQuery
    ) -> GetReturnExecutionResultDTO | None:
        """Декодирует конкретный DTO собственного сценария с Decimal и UUID."""
        statement = (
            select(ReturnPostingRequestModel)
            .where(ReturnPostingRequestModel.execution_id == query.identifier)
            .execution_options(populate_existing=True)
        )
        model = (await self._session.scalars(statement)).one_or_none()
        if model is None:
            return None
        if model.result is None:
            raise RuntimeError(
                "Завершённое исполнение не содержит первоначального результата."
            )
        return TypeAdapter(GetReturnExecutionResultDTO).validate_python(model.result)
